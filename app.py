from flask import Flask, render_template, request, session, redirect, url_for, flash
from pylxd import Client
import pylxd.exceptions

app = Flask(__name__)
# Session security ke liye ise badalna zaroori hai!
app.secret_key = 'zatrixtestkey_highly_secret_and_unique'

# --- LXD Connection Setup ---
try:
    # Local LXD daemon se connect karne ki koshish
    client = Client()
    
    # Connection check karne ka sahi tareeka: containers list karne ki koshish
    client.containers.all() 
    
    LXD_STATUS = True
    print("✅ Successfully connected to LXD.")
except Exception as e:
    print(f"❌ LXD Connection Error: {e}")
    print("⚠️ Important: Ensure the user running this script is in the 'lxd' group and LXD is initialized.")
    LXD_STATUS = False


@app.route('/', methods=['GET', 'POST'])
def index():
    # Agar LXD connect nahi hua toh error dikhao
    if not LXD_STATUS:
        # index.html mein lxd_error=True bhejo taaki wahan message dikhe
        return render_template('index.html', lxd_error=True)
        
    if request.method == 'POST':
        container_name = request.form.get('container_name').strip().lower()
        
        if not container_name:
            flash("Container Name khaali nahi ho sakta.", "danger")
            return render_template('index.html', lxd_error=False)

        # Container existence check
        try:
            if client.containers.exists(container_name):
                session['container_name'] = container_name
                return redirect(url_for('dashboard'))
            else:
                flash(f"❌ Container **'{container_name}'** ZatrixNodes par nahi mila! Sahi naam daalo.", "danger")
        except Exception as e:
            flash(f"Error accessing LXD while searching: {str(e)}", "danger")
            
    return render_template('index.html', lxd_error=False)


@app.route('/dashboard')
def dashboard():
    # Session aur LXD status check
    if not LXD_STATUS or 'container_name' not in session:
        return redirect(url_for('index'))
    
    c_name = session['container_name']
    
    try:
        container = client.containers.get(c_name)
        state = container.status  # Running, Stopped, etc.
        
        ip = "N/A"
        if state == "Running":
            # State info fetch karna
            state_data = container.state()
            
            # eth0 ka IP address nikalna
            if 'eth0' in state_data.network:
                addresses = state_data.network['eth0']['addresses']
                for addr in addresses:
                    if addr['family'] == 'inet':
                        ip = addr['address']
                        break
        
        return render_template('dashboard.html', name=c_name, status=state, ip=ip)
        
    except pylxd.exceptions.NotFound:
        session.pop('container_name', None)
        flash("⚠️ **Alert:** Yeh VPS ab exist nahi karta! Shuru se shuru karein.", "warning")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"❌ Dashboard load karte samay error aaya: {str(e)}", "danger")
        return redirect(url_for('index'))


@app.route('/action/<action_type>')
def action(action_type):
    # Session aur LXD status check
    if not LXD_STATUS or 'container_name' not in session:
        return redirect(url_for('index'))

    c_name = session['container_name']
    
    try:
        container = client.containers.get(c_name)
        
        # Action logic
        if action_type == 'start':
            if container.status != 'Running':
                container.start(wait=True, timeout=30)
                flash(f"✅ **VPS ({c_name})** successfully **Started!** Welcome back online.", "success")
            else:
                flash(f"ℹ️ **VPS ({c_name})** toh pehle se hi **Running** hai.", "info")
                
        elif action_type == 'stop':
            if container.status == 'Running':
                # Force=True use karna recommended hai agar jaldi stop karna ho
                container.stop(wait=True, timeout=30) 
                flash(f"🛑 **VPS ({c_name})** successfully **Stopped!** Data saved.", "warning")
            else:
                flash(f"ℹ️ **VPS ({c_name})** toh pehle se hi **Stopped** hai.", "info")

        elif action_type == 'restart':
            container.restart(wait=True, timeout=60)
            flash(f"🔄 **VPS ({c_name})** successfully **Restarted!** Back online in a moment.", "info")
            
        else:
            flash(f"❌ Invalid action: {action_type}.", "danger")
            
    except pylxd.exceptions.NotFound:
        session.pop('container_name', None)
        flash("⚠️ VPS not found during action. Please try accessing again.", "warning")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"❌ Action '{action_type}' ke dauraan bada error aaya: {str(e)}", "danger")

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('container_name', None)
    flash("👋 Logged out. Enter new VPS name to access.", "primary")
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Hosting ke liye: host='0.0.0.0'
    # Testing ke liye: debug=True
    app.run(host='0.0.0.0', port=5000, debug=True)
