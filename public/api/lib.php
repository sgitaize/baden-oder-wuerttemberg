<?php
// Shared helpers: config, database, captcha, rate limiting.
declare(strict_types=1);

const CAPTCHA_MAX = 60000;      // proof-of-work search space (~1–2 s in a browser)
const CAPTCHA_TTL = 900;        // seconds a challenge stays valid
const LIMIT_PER_HOUR = 6;       // posts per visitor and hour (stories + feedback)

function config(): array {
    static $cfg = null;
    if ($cfg !== null) return $cfg;
    $cfg = [
        'db_path' => __DIR__ . '/data/bow.sqlite',
        'admin_token' => '',
        'admin_mail' => '',
        'mail_from' => '',
    ];
    if (is_file(__DIR__ . '/config.php')) {
        $cfg = array_merge($cfg, require __DIR__ . '/config.php');
    }
    return $cfg;
}

function db(): PDO {
    static $pdo = null;
    if ($pdo) return $pdo;
    $path = config()['db_path'];
    if (!is_dir(dirname($path))) mkdir(dirname($path), 0750, true);
    $pdo = new PDO('sqlite:' . $path, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
    $pdo->exec('PRAGMA journal_mode = WAL; PRAGMA busy_timeout = 3000;');
    $pdo->exec('CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY, place INTEGER NOT NULL, place_name TEXT NOT NULL, author TEXT, body TEXT NOT NULL,
        created INTEGER NOT NULL, ip_hash TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0)');
    $pdo->exec('CREATE INDEX IF NOT EXISTS stories_place ON stories(place, hidden)');
    $pdo->exec('CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY, place INTEGER NOT NULL, place_name TEXT NOT NULL, state TEXT, suggested TEXT,
        message TEXT NOT NULL, email TEXT, created INTEGER NOT NULL, ip_hash TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)');
    $pdo->exec('CREATE TABLE IF NOT EXISTS captcha_used (challenge TEXT PRIMARY KEY, created INTEGER NOT NULL)');
    $pdo->exec('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)');
    return $pdo;
}

// Random server secret, created on first use and kept in the database (not in the repo).
function secret(): string {
    $row = db()->query("SELECT v FROM meta WHERE k = 'secret'")->fetch();
    if ($row) return $row['v'];
    $s = bin2hex(random_bytes(32));
    db()->prepare("INSERT OR IGNORE INTO meta (k, v) VALUES ('secret', ?)")->execute([$s]);
    return db()->query("SELECT v FROM meta WHERE k = 'secret'")->fetch()['v'];
}

// Daily rotating, non-reversible visitor hash – the IP itself is never stored.
function ip_hash(): string {
    return substr(hash_hmac('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . gmdate('Y-m-d'), secret()), 0, 24);
}

function json_out(array $data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function fail(string $msg, int $status = 400): never {
    json_out(['error' => $msg], $status);
}

function captcha_challenge(): array {
    $salt = bin2hex(random_bytes(12)) . '?expires=' . (time() + CAPTCHA_TTL);
    $number = random_int(0, CAPTCHA_MAX);
    $challenge = hash('sha256', $salt . $number);
    return [
        'algorithm' => 'SHA-256',
        'challenge' => $challenge,
        'maxnumber' => CAPTCHA_MAX,
        'salt' => $salt,
        'signature' => hash_hmac('sha256', $challenge, secret()),
    ];
}

function captcha_verify(string $payload): bool {
    $p = json_decode((string) base64_decode($payload, true), true);
    if (!is_array($p) || !isset($p['challenge'], $p['number'], $p['salt'], $p['signature'])) return false;
    if (!preg_match('/\?expires=(\d+)$/', (string) $p['salt'], $m) || (int) $m[1] < time()) return false;
    if (!hash_equals(hash_hmac('sha256', (string) $p['challenge'], secret()), (string) $p['signature'])) return false;
    if (!hash_equals(hash('sha256', $p['salt'] . (int) $p['number']), (string) $p['challenge'])) return false;
    // Each solved challenge only once
    db()->prepare('DELETE FROM captcha_used WHERE created < ?')->execute([time() - 2 * CAPTCHA_TTL]);
    $st = db()->prepare('INSERT OR IGNORE INTO captcha_used (challenge, created) VALUES (?, ?)');
    $st->execute([$p['challenge'], time()]);
    return $st->rowCount() === 1;
}

function rate_limited(string $ip): bool {
    $since = time() - 3600;
    $n = 0;
    foreach (['stories', 'feedback'] as $t) {
        $st = db()->prepare("SELECT COUNT(*) FROM $t WHERE ip_hash = ? AND created > ?");
        $st->execute([$ip, $since]);
        $n += (int) $st->fetchColumn();
    }
    return $n >= LIMIT_PER_HOUR;
}

// mbstring is not guaranteed on shared hosting
function u_len(string $s): int {
    return (int) preg_match_all('/./su', $s);
}

function u_sub(string $s, int $max): string {
    return preg_match('/^.{0,' . $max . '}/su', $s, $m) ? $m[0] : '';
}

function clean(mixed $s, int $max): string {
    $s = trim(str_replace("\r", '', (string) $s));
    $s = preg_replace('/[\x00-\x08\x0B-\x1F\x7F]/u', '', $s) ?? '';
    $s = preg_replace("/\n{3,}/", "\n\n", $s) ?? '';
    return u_sub($s, $max);
}

function notify(string $subject, string $text): void {
    $cfg = config();
    if (!$cfg['admin_mail']) return;
    $headers = 'Content-Type: text/plain; charset=utf-8';
    if ($cfg['mail_from']) $headers .= "\r\nFrom: " . $cfg['mail_from'];
    @mail($cfg['admin_mail'], '=?UTF-8?B?' . base64_encode($subject) . '?=', $text, $headers);
}
