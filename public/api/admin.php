<?php
// Minimal moderation page: feedback list, hide/show/delete stories. Login with ADMIN token from config.php.
declare(strict_types=1);
require __DIR__ . '/lib.php';

session_name('bowadmin');
session_set_cookie_params(['httponly' => true, 'secure' => !empty($_SERVER['HTTPS']), 'samesite' => 'Strict']);
session_start();
header('X-Robots-Tag: noindex');
header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'");

$token = config()['admin_token'];
$h = fn($s) => htmlspecialchars((string) $s, ENT_QUOTES);

if (isset($_POST['token'])) {
    if ($token !== '' && hash_equals($token, (string) $_POST['token'])) {
        session_regenerate_id(true);
        $_SESSION['ok'] = true;
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    } else {
        sleep(2);
    }
    header('Location: admin.php');
    exit;
}

if (empty($_SESSION['ok'])) {
    echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Moderation</title>'
        . '<body style="font-family:system-ui;background:#14110f;color:#eee;display:grid;place-items:center;height:100vh">'
        . '<form method="post"><h1>Moderation</h1><input type="password" name="token" placeholder="Admin-Token" autofocus style="padding:.6rem"> <button>Anmelden</button></form>';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && hash_equals($_SESSION['csrf'], (string) ($_POST['csrf'] ?? ''))) {
    $id = (int) ($_POST['id'] ?? 0);
    match ($_POST['do'] ?? '') {
        'hide' => db()->prepare('UPDATE stories SET hidden = 1 WHERE id = ?')->execute([$id]),
        'show' => db()->prepare('UPDATE stories SET hidden = 0 WHERE id = ?')->execute([$id]),
        'delete' => db()->prepare('DELETE FROM stories WHERE id = ?')->execute([$id]),
        'done' => db()->prepare('UPDATE feedback SET done = 1 WHERE id = ?')->execute([$id]),
        'open' => db()->prepare('UPDATE feedback SET done = 0 WHERE id = ?')->execute([$id]),
        'logout' => session_destroy(),
        default => null,
    };
    header('Location: admin.php');
    exit;
}

$csrf = $_SESSION['csrf'];
$btn = fn($do, $id, $label) => "<form method=post style=display:inline><input type=hidden name=csrf value=$csrf><input type=hidden name=id value=$id><button name=do value=$do>$label</button></form>";
$date = fn($t) => date('Y-m-d H:i', (int) $t);
$feedback = db()->query('SELECT * FROM feedback ORDER BY done, created DESC LIMIT 300')->fetchAll();
$stories = db()->query('SELECT * FROM stories ORDER BY created DESC LIMIT 300')->fetchAll();
?>
<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Moderation – Baden oder Württemberg</title>
<style>body{font-family:system-ui;background:#14110f;color:#eee;max-width:1000px;margin:auto;padding:1rem}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #333;padding:.5rem;vertical-align:top;text-align:left}a{color:#f0c24b}.muted{opacity:.5}pre{white-space:pre-wrap;margin:0;font:inherit}</style>
<?= $btn('logout', 0, 'Abmelden') ?>
<h1>Rückmeldungen zur Zuordnung (<?= count(array_filter($feedback, fn($f) => !$f['done'])) ?> offen)</h1>
<table><tr><th>Datum</th><th>Ort</th><th>Angezeigt → Vorschlag</th><th>Nachricht</th><th></th></tr>
<?php foreach ($feedback as $f): ?>
<tr class="<?= $f['done'] ? 'muted' : '' ?>"><td><?= $date($f['created']) ?></td>
<td><a href="../#ort/<?= (int) $f['place'] ?>"><?= $h($f['place_name']) ?></a></td>
<td><?= $h($f['state']) ?> → <?= $h($f['suggested']) ?></td>
<td><pre><?= $h($f['message']) ?></pre><?= $f['email'] ? '<small>' . $h($f['email']) . '</small>' : '' ?></td>
<td><?= $f['done'] ? $btn('open', $f['id'], 'wieder öffnen') : $btn('done', $f['id'], 'erledigt') ?></td></tr>
<?php endforeach ?>
</table>
<h1>Geschichten</h1>
<table><tr><th>Datum</th><th>Ort</th><th>Text</th><th></th></tr>
<?php foreach ($stories as $s): ?>
<tr class="<?= $s['hidden'] ? 'muted' : '' ?>"><td><?= $date($s['created']) ?></td>
<td><a href="../#ort/<?= (int) $s['place'] ?>"><?= $h($s['place_name']) ?></a></td>
<td><pre><?= $h($s['body']) ?></pre><small>— <?= $h($s['author'] ?: 'anonym') ?></small></td>
<td><?= $s['hidden'] ? $btn('show', $s['id'], 'einblenden') : $btn('hide', $s['id'], 'ausblenden') ?> <?= $btn('delete', $s['id'], 'löschen') ?></td></tr>
<?php endforeach ?>
</table>
