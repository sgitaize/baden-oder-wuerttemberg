<?php
// Liefert die Daten-JSONs vorkomprimiert aus (nginx auf dem Hosting komprimiert kein JSON).
// deploy.sh legt data/*.json.gz an; ohne .gz wird die normale Datei geschickt.
declare(strict_types=1);

$name = $_GET['f'] ?? '';
if (!in_array($name, ['places', 'borders', 'facts', 'stats'], true)) {
    http_response_code(404);
    exit;
}
$file = __DIR__ . "/data/$name.json";
$gz = "$file.gz";
$etag = '"' . filemtime($file) . '-' . filesize($file) . '"';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=3600');
header('ETag: ' . $etag);
header('Vary: Accept-Encoding');
if (($_SERVER['HTTP_IF_NONE_MATCH'] ?? '') === $etag) {
    http_response_code(304);
    exit;
}
if (is_file($gz) && str_contains($_SERVER['HTTP_ACCEPT_ENCODING'] ?? '', 'gzip')) {
    header('Content-Encoding: gzip');
    header('Content-Length: ' . filesize($gz));
    readfile($gz);
} else {
    header('Content-Length: ' . filesize($file));
    readfile($file);
}
