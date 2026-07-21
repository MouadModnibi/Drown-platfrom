# SSH Key Setup - Implementation Summary

## Overview

The `drown login` command now automatically handles SSH key setup, so users never need to manually run `ssh-keygen` or configure git remotes with custom key paths. After a successful login, `git push platform main` works automatically with zero additional configuration.

## What Happens During `drown login`

1. **Authentication** (existing behavior, unchanged)
   - Prompts for username/password
   - Calls `POST /api/auth/login`
   - Saves token to `~/.drown/config.json`

2. **SSH Key Generation** (new)
   - Checks if `~/.drown/id_ed25519` and `~/.drown/id_ed25519.pub` exist
   - If not: generates new ed25519 key pair using `ssh-keygen -t ed25519 -f ~/.drown/id_ed25519 -N ""`
   - Sets permissions to 600 on private key (Unix only, Windows handles differently)
   - If key already exists: skips generation, uses existing key

3. **Key Registration** (new)
   - Reads public key content from `~/.drown/id_ed25519.pub`
   - Calls `POST /api/keys/register` with `Authorization: Bearer <token>` header
   - Registers the public key with the platform for the logged-in user
   - If registration fails: prints warning but doesn't fail login (user can still use API commands)

4. **SSH Config Update** (new)
   - Updates `~/.ssh/config` to add/update `Host drown-platform` entry
   - Safe parsing: only modifies drown-platform block, preserves all other Host entries
   - Atomic write: writes to temp file, then renames (prevents corruption)
   - Verification: reads back config to confirm Host block is present and well-formed
   - If verification fails: prints warning but doesn't fail login

## SSH Config Entry Added

```
Host drown-platform
    HostName 51.170.134.251
    User ubuntu
    IdentityFile ~/.drown/id_ed25519
    IdentitiesOnly yes
```

## Git Remote URL Changes

**Before** (required manual GIT_SSH_COMMAND or key specification):
```
ssh://ubuntu@51.170.134.251/home/ubuntu/git-hook-test/<app_name>.git
```

**After** (uses SSH config alias automatically):
```
ssh://ubuntu@drown-platform/home/ubuntu/git-hook-test/<app_name>.git
```

The `drown create` command now generates git remotes using the `drown-platform` host alias, so `git push platform main` automatically uses the registered key.

## User Experience

### Successful Login (First Time)
```
$ drown login
Login to Drown Platform
API: https://dashboard.dr0wn.duckdns.org

Username: mouad
Password: 

Authenticating...
✓ Logged in as mouad

Setting up SSH key for git push...
✓ Generated SSH key
✓ Registered key with platform
✓ SSH config updated — 'git push platform main' will work automatically
```

### Successful Login (Subsequent)
```
$ drown login
Login to Drown Platform
API: https://dashboard.dr0wn.duckdns.org

Username: mouad
Password: 

Authenticating...
✓ Logged in as mouad

Setting up SSH key for git push...
✓ Using existing SSH key
✓ Registered key with platform
✓ SSH config updated — 'git push platform main' will work automatically
```

### Partial Failure (Key Registration Fails)
```
$ drown login
Login to Drown Platform
API: https://dashboard.dr0wn.duckdns.org

Username: mouad
Password: 

Authenticating...
✓ Logged in as mouad

Setting up SSH key for git push...
✓ Generated SSH key
⚠ Failed to register SSH key: Connection timeout
  You can still use 'drown apps', 'drown scale', etc.
  Git push may require manual SSH configuration.
```

### ssh-keygen Not Available
```
$ drown login
Login to Drown Platform
API: https://dashboard.dr0wn.duckdns.org

Username: mouad
Password: 

Authenticating...
✓ Logged in as mouad

Setting up SSH key for git push...
✗ ssh-keygen not found. Please install OpenSSH or Git for Windows.
```

## Implementation Details

### Files Modified

1. **drown/config.py**
   - Added `SSH_PRIVATE_KEY` and `SSH_PUBLIC_KEY` constants
   - Added `generate_ssh_key()` - generates ed25519 key pair
   - Added `read_public_key()` - reads public key file
   - Added `update_ssh_config()` - safely updates ~/.ssh/config
   - Added `setup_ssh_key()` - orchestrates the entire setup process

2. **drown/api.py**
   - Added `register_ssh_key(token, public_key)` - calls POST /api/keys/register

3. **drown/cli.py**
   - Updated `login()` command to call `setup_ssh_key()` after successful auth
   - Updated `create()` command to use `drown-platform` host alias in git remotes

4. **README.md**
   - Added documentation for SSH key setup process
   - Added Windows path examples
   - Updated requirements to mention OpenSSH

### SSH Config File Handling (Safety Features)

1. **Non-destructive parsing**: Only recognizes `Host` lines, treats everything else as opaque
2. **Preserves existing entries**: Never touches other Host blocks
3. **Atomic write**: Writes to temp file first, only replaces on success
4. **Idempotent**: Running multiple times produces same result
5. **Verification**: Reads back config after write to confirm success
6. **Error handling**: Gracefully handles missing directories, permission errors, etc.

### Windows Compatibility

- Tested on Windows 10/11 with PowerShell
- `Path.home()` correctly resolves to `C:\Users\<username>\`
- OpenSSH is built into Windows 10+ (ssh-keygen available by default)
- Forward slashes used in IdentityFile path for cross-platform compatibility
- Permission setting (chmod 600) skipped on Windows (handled differently by OS)

### Testing Done

- ✅ Fresh install (no SSH key, no config)
- ✅ Existing key reuse
- ✅ Existing config with other Host entries (preserved)
- ✅ Existing drown-platform entry (updated, not duplicated)
- ✅ Idempotent (multiple runs don't duplicate)
- ✅ Windows path resolution (C:\Users\Microsoft\...)
- ✅ Config verification (reads back after write)
- ✅ Public key format (valid ssh-ed25519)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| ssh-keygen not available | Clear error message, suggests installing OpenSSH/Git for Windows |
| Key generation fails | Error message with stderr output |
| Public key unreadable | Error message, stops setup |
| Key registration network error | Warning message, login still succeeds for API use |
| Key registration server error | Warning message, login still succeeds for API use |
| SSH config write fails | Warning message, login still succeeds for API use |
| SSH config verification fails | Warning message, login still succeeds for API use |

## Future Enhancements (Not Implemented Yet)

- Support for multiple SSH keys (key rotation)
- Key expiration/renewal workflow
- Option to use existing keys instead of generating new ones
- Support for passphrase-protected keys (with ssh-agent)
- Windows SSH agent integration

## API Endpoint Used

**POST /api/keys/register**
- Headers: `Authorization: Bearer <token>`
- Body: `{"public_key": "ssh-ed25519 AAAA... comment"}`
- Response: `{"message": "Key registered successfully"}` or `{"error": "..."}`

This endpoint already exists and is tested - no server-side changes needed.
