from fabric import task
import os
import yaml
import re
from getpass import getpass
import tempfile


@task
def install_git_template(c):
    """Install DVC git hooks as system-wide templates using config.yml"""
    # Read config.yml to get server details
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
        # Get first non-localhost origin
        for origin in config['cors']['allowed_origins']:
            if not re.match(r'http://(localhost|127\.0\.0\.1)', origin):
                server_url = f"{origin}/api/data/upload-metadata"
                break
        else:
            # Fallback to localhost if no public origins found
            server_url = "http://localhost:7123/api/data/upload-metadata"
    
    # Get sudo password if needed
    sudo_password = getpass("Enter sudo password for remote host: ")
    c.config.sudo.password = sudo_password
    
    # Create template directory
    template_dir = "/usr/share/git-core/templates"
    hooks_dir = f"{template_dir}/hooks"
    c.sudo(f"mkdir -p {hooks_dir}")
    
    # Upload and update hooks
    for hook in ["post-commit", "pre-push"]:
        # Read hook content
        hook_path = os.path.join(os.path.dirname(__file__), hook)
        with open(hook_path, "r") as f:
            content = f.read()
        
        # Update SERVER_URL
        updated_content = content.replace(
            'SERVER_URL="http://localhost:8000/api/data/upload-metadata"',
            f'SERVER_URL="{server_url}"')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
            temp_file.write(updated_content)
            temp_path = temp_file.name
        
        # Upload to remote
        c.put(temp_path, f"/tmp/{hook}")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Move to template directory and set executable
        c.sudo(f"cp /tmp/{hook} {hooks_dir}/{hook}")
        c.sudo(f"chmod 755 {hooks_dir}/{hook}")
        c.sudo(f"chown root:root {hooks_dir}/{hook}")
    
    # Configure git to use system template
    c.sudo(f"git config --system init.templateDir {template_dir}")
    print(
        f"✓ System-level DVC metadata hooks installed on server {c.host} with DVC server {server_url}!"
    )

