# Remove owner SSH access

Connect using the key that is being removed:

```sh
ssh -i "$HOME/.ssh/fibreseek_owner_ed25519" \
  anisoprint@192.168.50.113
```

On the printer, first make a backup:

```sh
cp -a ~/.ssh/authorized_keys ~/.ssh/authorized_keys.before-owner-key-removal
```

Display the fingerprint of each authorized key:

```sh
ssh-keygen -lf ~/.ssh/authorized_keys
```

Remove only the line matching the public key you intend to revoke. One reliable
method is to copy `authorized_keys` to a temporary file, edit it, inspect the
result, and then replace the original:

```sh
cp ~/.ssh/authorized_keys /tmp/authorized_keys.edit
nano /tmp/authorized_keys.edit
ssh-keygen -lf /tmp/authorized_keys.edit
install -m 600 /tmp/authorized_keys.edit ~/.ssh/authorized_keys
rm /tmp/authorized_keys.edit
```

Keep the current SSH session open and test from a second terminal. The removed
key should fail and any keys you intended to preserve should still work.

To restore the backup from the original session:

```sh
install -m 600 ~/.ssh/authorized_keys.before-owner-key-removal \
  ~/.ssh/authorized_keys
```
