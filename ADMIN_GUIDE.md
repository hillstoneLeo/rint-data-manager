# Admin User Management Guide

## Registering the First Admin User

To register as the first admin in the system, you have two options:

### Web Interface Method

1. **Navigate to the admin registration page**: Go to `/register-admin` in your browser
2. **Fill out the form**: Enter your email and password (minimum 8 characters)
3. **Submit**: Click "Register Admin"

The system will only allow admin registration if no admin users already exist. Once the first admin is created, this endpoint becomes disabled.

### Command Line Method

```bash
python db_manager.py make-admin <email>
```

The admin registration bypasses email domain restrictions and creates the user with admin privileges immediately.

## Web Interface Admin Capabilities

Admin users can manage other users through the web interface at `/admin`:

### Available Actions:
1. **View all users** - See complete list of users with their admin status
2. **Toggle admin status** - Promote/demote users to/from admin role
3. **Reset user passwords** - Set new passwords for any user (except self)
4. **Delete users** - Remove users from the system (except self)

### Security Protections:
- Admins cannot modify their own admin status
- Admins cannot delete their own account
- Admins cannot reset their own password through admin panel
- All actions require valid admin authentication

## Command Line Database Management

For direct database access, use the `db_manager.py` script:

### List all users:
```bash
python db_manager.py list
```

### Reset user password:
```bash
python db_manager.py reset-password <email> <new_password>
```

### Grant admin privileges:
```bash
python db_manager.py make-admin <email>
```

### Remove admin privileges:
```bash
python db_manager.py remove-admin <email>
```

### Delete user:
```bash
python db_manager.py delete-user <email>
```

## Direct Database Access

The database is located at `./rint_data_manager.db` (SQLite format).

### Using sqlite3

```bash
sudo apt install sqlite3
sqlite3 rint_data_manager.db

# List tables
.tables

# View users
SELECT * FROM users;

# Update password (requires bcrypt hash)
UPDATE users SET hashed_password = '$2b$12$...' WHERE email = 'user@example.com';

# Toggle admin status
UPDATE users SET is_admin = 1 WHERE email = 'user@example.com';
```

### Important Notes:
- Passwords are stored as bcrypt hashes, not plain text
- Use the `db_manager.py` script for password operations as it handles bcrypt hashing
- Direct database manipulation requires knowledge of bcrypt hashing
- Always backup the database before making direct changes

## Password Security

- All passwords are hashed using bcrypt with automatic salt generation
- The system never stores plain text passwords
- Password validation requires minimum 8 characters
- Admin password resets through web interface enforce password length requirements

## Email Domain Restrictions

- User registration is restricted to configured email domains (default: hillstonenet.com)
- Admin registration bypasses email domain restrictions
- Configuration is in `config.yml` under `auth.email_suffix_regex`
