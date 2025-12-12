from flask import Flask, render_template, request, session, redirect, url_for, flash
from pylxd import Client
import pylxd.exceptions

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_me'  # Session ke liye zaroori hai

# LXD Client connect karo
try:
    client = Client()
except Exception as e:
    print(f"Error connecting to LXD: {e}")
    # Note: Ensure user is in 'lxd' group

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        container_name = request.form.get('container_name')
        
        # Check karo container exist karta hai ya nahi
        if client.containers.exists(container_name):
            session['container_name'] = container_name
            return redirect(url_for('dashboard'))
        else:
            flash(f"Container '{container_name}' nahi mila! Sahi naam daalo.", "danger")
            
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'container_name' not in session:
        return redirect(url_for('index'))
    
    c_name = session['container_name']
    try:
        container = client.containers.get(c_name)
        state = container.status  # Running, Stopped, etc.
        # IP Address nikalne ke liye
        ip = "N/A"
        if state == "Running":
            addresses = container.state().network['eth0']['addresses']
            for addr in addresses:
                if addr['family'] == 'inet':
                    ip = addr['address']
        
        return render_template('dashboard.html', name=c_name, status=state, ip=ip)
    except pylxd.exceptions.NotFound:
        session.pop('container_name', None)
        flash("Container delete ho gaya shayad.", "warning")
        return redirect(url_for('index'))

@app.route('/action/<action_type>')
def action(action_type):
    if 'container_name' not in session:
        return redirect(url_for('index'))

    c_name = session['container_name']
    container = client.containers.get(c_name)

    try:
        if action_type == 'start':
            if container.status != 'Running':
                container.start(wait=True)
                flash(f"{c_name} Start ho gaya!", "success")
        elif action_type == 'stop':
            if container.status == 'Running':
                container.stop(wait=True)
                flash(f"{c_name} Stop ho gaya!", "warning")
        elif action_type == 'restart':
            container.restart(wait=True)
            flash(f"{c_name} Restart ho gaya!", "info")
            
    except Exception as e:
        flash(f"Error aaya: {str(e)}", "danger")

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('container_name', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 0.0.0.0 ka matlab ye network pe available hoga
    app.run(host='0.0.0.0', port=5000, debug=True)
              
