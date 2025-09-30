from fabric import task
import os
from getpass import getpass


@task
def install_git_template(c):
    """Install DVC git hooks as system-wide templates using config.yml"""
    
    # Get sudo password if needed
    sudo_password = getpass("Enter sudo password for remote host: ")
    c.config.sudo.password = sudo_password

    # Create template directory
    template_dir = "/usr/share/git-core/templates"
    hooks_dir = f"{template_dir}/hooks"
    c.sudo(f"mkdir -p {hooks_dir}")

    # Upload pre-generated hooks (no string replacement needed!)
    for hook in ["post-commit", "pre-push"]:
        hook_path = os.path.join(os.path.dirname(__file__), hook)
        
        # Upload to remote
        c.put(hook_path, f"/tmp/{hook}")
        
        # Move to template directory and set executable
        c.sudo(f"cp /tmp/{hook} {hooks_dir}/{hook}")
        c.sudo(f"chmod 755 {hooks_dir}/{hook}")
        c.sudo(f"chown root:root {hooks_dir}/{hook}")

    # Configure git to use system template
    c.sudo(f"git config --system init.templateDir {template_dir}")
    print(f"✓ System-level DVC metadata hooks installed on server {c.host}!")