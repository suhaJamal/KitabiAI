<?php
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

$name         = trim($_POST['name'] ?? '');
$organization = trim($_POST['organization'] ?? '');
$email        = trim($_POST['email'] ?? '');
$books        = trim($_POST['books'] ?? '');
$language     = trim($_POST['language'] ?? '');
$message      = trim($_POST['message'] ?? '');

if (!$name || !$email || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Name and valid email are required']);
    exit;
}

require 'phpmailer/Exception.php';
require 'phpmailer/PHPMailer.php';
require 'phpmailer/SMTP.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\SMTP;
use PHPMailer\PHPMailer\Exception;

$mail = new PHPMailer(true);

try {
    $mail->isSMTP();
    $mail->Host       = 'smtp.hostinger.com';
    $mail->SMTPAuth   = true;
    $mail->Username   = 'hello@kitabiai.com';
    $mail->Password   = 'dykti1997Awb!@#';
    $mail->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;
    $mail->Port       = 465;
    $mail->CharSet    = 'UTF-8';

    $mail->setFrom('hello@kitabiai.com', 'KitabiAI Website');
    $mail->addAddress('hello@kitabiai.com', 'KitabiAI');
    $mail->addReplyTo($email, $name);

    $mail->Subject = "Early Access Request from $name" . ($organization ? " ($organization)" : '');
    $mail->Body    = implode("\n", [
        "Name:         $name",
        "Organization: $organization",
        "Email:        $email",
        "Books:        $books",
        "Language:     $language",
        "",
        "Message:",
        $message,
    ]);

    $mail->send();
    echo json_encode(['success' => true, 'message' => 'Message sent']);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Mailer error: ' . $mail->ErrorInfo]);
}
