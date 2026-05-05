<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Join Csabolanta</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            background-color: #0b0e14;
            color: #cbd5e1;
            -webkit-font-smoothing: antialiased;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .card {
            background-color: #1c222d;
            border: 1px solid #2d3544;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            background: linear-gradient(180deg, #1c222d 0%, #151921 100%);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            font-family: 'Georgia', serif;
            font-weight: 900;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: -0.05em;
            color: #ffffff;
            font-size: 28px;
            margin: 0;
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }
        .title {
            color: #ffffff;
            font-size: 24px;
            font-weight: bold;
            margin-top: 0;
            margin-bottom: 16px;
        }
        .content {
            font-size: 16px;
            line-height: 1.6;
            color: #94a3b8;
        }
        .accent {
            color: #38bdf8;
            font-weight: bold;
        }
        .button-container {
            text-align: center;
            margin: 32px 0;
        }
        .button {
            display: inline-block;
            background-color: #38bdf8;
            color: #0b0e14;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 14px;
            box-shadow: 0 4px 14px 0 rgba(56, 189, 248, 0.39);
        }
        .footer {
            margin-top: 24px;
            font-size: 12px;
            color: #64748b;
            text-align: center;
            border-top: 1px solid #2d3544;
            padding-top: 16px;
        }
        .link {
            color: #38bdf8;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h1 class="logo">CSABOLANTA</h1>
            </div>
            
            <h2 class="title">You've been invited!</h2>
            
            <div class="content">
                <p><span class="accent">{{ $inviterName }}</span> has invited you to join Csabolanta, the ultimate flight tracking platform for X-Plane and MSFS.</p>
                <p>Click the button below to create your account and set your password to get started tracking your flights.</p>
            </div>
            
            <div class="button-container">
                <a href="{{ $registerUrl }}" class="button">Create Account</a>
            </div>
            
            <div class="footer">
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <a href="{{ $registerUrl }}" class="link">{{ $registerUrl }}</a>
            </div>
        </div>
    </div>
</body>
</html>