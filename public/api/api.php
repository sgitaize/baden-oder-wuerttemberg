<?php
// Public API: GET ?a=captcha | GET ?a=stories&place=<osm id> | POST {a: story|feedback, ...}
declare(strict_types=1);
require __DIR__ . '/lib.php';

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $a = $_GET['a'] ?? '';
        if ($a === 'captcha') json_out(captcha_challenge());
        if ($a === 'stories') {
            $place = (int) ($_GET['place'] ?? 0);
            $st = db()->prepare('SELECT id, author, body, created FROM stories WHERE place = ? AND hidden = 0 ORDER BY created DESC LIMIT 200');
            $st->execute([$place]);
            json_out(['stories' => $st->fetchAll()]);
        }
        fail('Unbekannte Aktion.', 404);
    }

    if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail('Methode nicht erlaubt.', 405);
    $in = json_decode((string) file_get_contents('php://input'), true);
    if (!is_array($in)) fail('Ungültige Anfrage.');

    // Honeypot: bots fill every field; pretend success
    if (!empty($in['website'])) json_out(['ok' => true, 'story' => ['author' => '', 'body' => '', 'created' => time()]]);

    $a = $in['a'] ?? '';
    $place = (int) ($in['place'] ?? 0);
    $placeName = clean($in['placeName'] ?? '', 120);
    if ($place <= 0 || $placeName === '') fail('Ort fehlt.');
    if (!captcha_verify((string) ($in['captcha'] ?? ''))) fail('Die Roboter-Prüfung ist abgelaufen oder ungültig. Bitte nochmal bestätigen.', 403);
    purge_old();
    $ip = ip_hash();
    if (rate_limited($ip)) fail('Du hast gerade schon einiges geschickt – bitte versuch es später nochmal.', 429);

    if ($a === 'story') {
        $author = clean($in['author'] ?? '', 80);
        $body = clean($in['body'] ?? '', 3000);
        if (u_len($body) < 10) fail('Die Geschichte ist etwas kurz – erzähl ruhig mehr.');
        if (preg_match_all('#https?://#i', $body) > 2) fail('Bitte höchstens zwei Links pro Geschichte.');
        $now = time();
        db()->prepare('INSERT INTO stories (place, place_name, author, body, created, ip_hash) VALUES (?, ?, ?, ?, ?, ?)')
            ->execute([$place, $placeName, $author, $body, $now, $ip]);
        notify("Neue Geschichte: $placeName", "$author schreibt zu $placeName:\n\n$body");
        json_out(['ok' => true, 'story' => ['id' => (int) db()->lastInsertId(), 'author' => $author, 'body' => $body, 'created' => $now]]);
    }

    if ($a === 'feedback') {
        $message = clean($in['message'] ?? '', 2000);
        $email = clean($in['email'] ?? '', 200);
        if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) fail('Die E-Mail-Adresse sieht ungültig aus.');
        $state = in_array($in['state'] ?? '', ['B', 'W', 'H', 'X'], true) ? $in['state'] : '';
        $suggested = in_array($in['suggested'] ?? '', ['B', 'W', 'H', 'X', '?'], true) ? $in['suggested'] : '?';
        if (u_len($message) < 5) fail('Bitte beschreib kurz, was nicht stimmt.');
        db()->prepare('INSERT INTO feedback (place, place_name, state, suggested, message, email, created, ip_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
            ->execute([$place, $placeName, $state, $suggested, $message, $email, time(), $ip]);
        notify("Rückmeldung: $placeName", "Ort: $placeName (OSM $place)\nAngezeigt: $state, Vorschlag: $suggested\nE-Mail: $email\n\n$message");
        json_out(['ok' => true]);
    }

    fail('Unbekannte Aktion.', 404);
} catch (Throwable $e) {
    error_log('bow api: ' . $e->getMessage());
    fail('Serverfehler – bitte später nochmal versuchen.', 500);
}
