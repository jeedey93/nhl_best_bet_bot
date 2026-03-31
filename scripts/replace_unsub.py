import sys

placeholder = '$' + '{UNSUBSCRIBE_URL}'
with open('/tmp/email_body_final.html', 'r') as f:
    html = f.read()
html = html.replace(placeholder, sys.argv[1])
with open('/tmp/email_personal.html', 'w') as f:
    f.write(html)
