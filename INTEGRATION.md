# Integration Instructions

To enable the new Compliance Cog (GDPR commands), you must update `bot/main.py`.

## Step 1: Open `bot/main.py`

## Step 2: Locate the `setup_hook` method and the `extensions` list.

It should look like this:

```python
        # Load Cogs
        extensions = [
            "bot.cogs.authentication",
        ]
```

## Step 3: Add the Compliance Cog to the list.

Add `"bot.cogs.compliance.cog"` to the list.

```python
        # Load Cogs
        extensions = [
            "bot.cogs.authentication",
            "bot.cogs.compliance.cog",  # <--- ADD THIS LINE
        ]
```

## Step 4: Save and Restart.

Save `bot/main.py` and restart the bot. The commands `!privacy_export` and `!privacy_forget` will now be available.
