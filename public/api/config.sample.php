<?php
// Copy to config.php on the server (deploy.sh does this from .env). Never commit config.php.
return [
    'admin_token' => 'long-random-string',       // login for api/admin.php
    'admin_mail' => '',                          // optional: notifications for new posts
    'mail_from' => '',                           // optional sender address
    // 'db_path' => __DIR__ . '/data/bow.sqlite',
];
