from flask import Flask, render_template_string, request, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# In-memory task storage
tasks = []

# Function to extract the user's name from the email address
def extract_name_from_email(email):
    return email.split('@')[0]

# HTML template with dark theme CSS
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1e1e1e;
            color: #e0e0e0;
            margin: 0;
            padding: 0;
        }
        .container {
            width: 50%;
            margin: 20px auto;
            padding: 20px;
            background-color: #2c2c2c;
            border-radius: 8px;
        }
        h2 {
            text-align: center;
            color: #ffffff;
        }
        form {
            margin-bottom: 20px;
            background-color: #333333;
            padding: 15px;
            border-radius: 8px;
        }
        input, select {
            padding: 8px;
            margin: 5px 0;
            width: calc(100% - 20px);
            box-sizing: border-box;
            border: 1px solid #444444;
            border-radius: 4px;
            background-color: #555555;
            color: #e0e0e0;
        }
        button {
            padding: 10px;
            color: #e0e0e0;
            background-color: #007bff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .task {
            border: 1px solid #444444;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #333333;
            border-radius: 8px;
        }
        .task p {
            margin: 0 0 10px;
        }
        .task button {
            background-color: #dc3545;
        }
        .task button:hover {
            background-color: #c82333;
        }
        .done-button {
            background-color: #28a745;
        }
        .done-button:hover {
            background-color: #218838;
        }
        .footer {
            text-align: center;
            color: #e0e0e0;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Task Manager</h2>
        <form method="post" action="/add_task">
            <input type="text" name="task" placeholder="Enter Task" required>
            <input type="date" name="deadline" required>
            <input type="email" name="email" placeholder="Enter Email" required>
            <select name="priority">
                <option value="High">High Priority</option>
                <option value="Medium">Medium Priority</option>
                <option value="Low">Low Priority</option>
            </select>
            <button type="submit">Add Task</button>
        </form>
        
        {% for task in sorted_tasks %}
        <div class="task">
            <p><strong>Task:</strong> {{ task.task }}</p>
            <p><strong>Deadline:</strong> {{ task.deadline }}</p>
            <p><strong>Email:</strong> {{ task.email }}</p>
            <p><strong>Priority:</strong> {{ task.priority }}</p>
            <form method="post" action="/mark_done">
                <input type="hidden" name="task" value="{{ task.task }}">
                <button type="submit" class="done-button">Mark as Done</button>
            </form>
            <form method="post" action="/delete_task" style="display:inline;">
                <input type="hidden" name="task" value="{{ task.task }}">
                <button type="submit">Delete Task</button>
            </form>
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>&copy; Niels Coert</p>
        </div>
    </div>
</body>
</html>
'''

# Function to send email
def send_email(to_email, subject, body):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    from_email = 'auto.mail.local@gmail.com'
    password = 'xrlr atel vakf krsu'

    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())

# Function to send task added email
def send_task_added_email(task):
    name = extract_name_from_email(task['email'])
    deadline_date = datetime.strptime(task['deadline'], '%Y-%m-%d')
    days_until_deadline = (deadline_date - datetime.now()).days

    warning_message = ""
    if (deadline_date - datetime.now()) <= timedelta(days=1):
        warning_message = "<p><strong>Warning:</strong> The deadline for this task is within the next 24 hours.</p>"

    send_email(
        task['email'],
        'Task Added',
        f"""
        <html>
        <body style="background-color: #ffffff; color: #000000;">
            <p>Hi {name},</p>
            <p>Your task '<strong>{task['task']}</strong>' has been successfully added.</p>
            <p>The deadline for this task is <strong>{task['deadline']}</strong>, which is in <strong>{days_until_deadline}</strong> days.</p>
            {warning_message}
            <p>Thank you for using our Task Manager!</p>
            <p>Best regards,<br>Task Manager Team</p>
        </body>
        </html>
        """
    )

# Function to send deadline reminder email
def send_deadline_reminder(task):
    name = extract_name_from_email(task['email'])
    send_email(
        task['email'],
        'Task Deadline Reminder',
        f"""
        <html>
        <body style="background-color: #ffffff; color: #000000;">
            <p>Hi {name},</p>
            <p>This is a reminder that your task '<strong>{task['task']}</strong>' is due tomorrow.</p>
            <p>The deadline is <strong>{task['deadline']}</strong>.</p>
            <p>Please ensure that the task is completed on time.</p>
            <p>Best regards,<br>Task Manager Team</p>
        </body>
        </html>
        """
    )

# Function to send task completed email
def send_task_completed_email(task):
    name = extract_name_from_email(task['email'])
    send_email(
        task['email'],
        'Task Completed',
        f"""
        <html>
        <body style="background-color: #ffffff; color: #000000;">
            <p>Hi {name},</p>
            <p>Congratulations! Your task '<strong>{task['task']}</strong>' has been marked as done.</p>
            <p>Thank you for using our Task Manager!</p>
            <p>Best regards,<br>Task Manager Team</p>
        </body>
        </html>
        """
    )

# Function to check deadlines
def check_deadlines():
    while True:
        now = datetime.now()
        for task in tasks[:]:
            task_deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
            if task_deadline - now <= timedelta(days=1):
                send_deadline_reminder(task)
                tasks.remove(task)
        time.sleep(3600)  # Check every hour

@app.route('/', methods=['GET'])
def index():
    # Sort tasks by priority
    priority_order = {'High': 1, 'Medium': 2, 'Low': 3}
    sorted_tasks = sorted(tasks, key=lambda t: priority_order[t['priority']])
    return render_template_string(HTML_TEMPLATE, sorted_tasks=sorted_tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    task = {
        'task': request.form['task'],
        'deadline': request.form['deadline'],
        'email': request.form['email'],
        'priority': request.form['priority']
    }
    tasks.append(task)
    send_task_added_email(task)
    return redirect(url_for('index'))

@app.route('/delete_task', methods=['POST'])
def delete_task():
    task_to_delete = request.form['task']
    global tasks
    tasks = [task for task in tasks if task['task'] != task_to_delete]
    return redirect(url_for('index'))

@app.route('/mark_done', methods=['POST'])
def mark_done():
    task_to_mark_done = request.form['task']
    global tasks
    for task in tasks[:]:
        if task['task'] == task_to_mark_done:
            tasks.remove(task)
            send_task_completed_email(task)
            break
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Start the deadline checking in a separate thread
    threading.Thread(target=check_deadlines, daemon=True).start()
    app.run(host='192.168.2.12', port=5000)
