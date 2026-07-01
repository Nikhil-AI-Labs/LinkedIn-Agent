# Kimi WebBridge Setup Guide

## What is Kimi WebBridge?

Kimi WebBridge is a browser extension that allows your backend to control your real browser session. This means:
- ✅ Uses your actual logged-in LinkedIn session
- ✅ No need to manage credentials
- ✅ Lower detection risk (real browser, no automation markers)
- ✅ Can perform all LinkedIn actions: post, comment, like, fetch feed, etc.

## Installation Steps

### 1. Install Kimi WebBridge Extension

**For Microsoft Edge:**
1. Download the Kimi WebBridge extension files
2. Open Edge and go to `edge://extensions/`
3. Enable "Developer mode" (toggle in bottom-left)
4. Click "Load unpacked"
5. Select the Kimi WebBridge extension folder
6. The extension should now appear in your extensions list

**For Chrome:**
1. Download the Kimi WebBridge extension files
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top-right)
4. Click "Load unpacked"
5. Select the Kimi WebBridge extension folder
6. The extension should now appear in your extensions list

### 2. Start Your Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see in the logs:
```
Kimi WebBridge server started on port 10086
Starting KimiBridgeServer on ws://127.0.0.1:10086/ws
```

### 3. Connect the Extension

1. **Open your browser** (Edge or Chrome where you installed the extension)
2. **Log into LinkedIn** in that browser
3. **Click on the Kimi WebBridge extension icon** in your toolbar
4. The extension should automatically connect to `ws://127.0.0.1:10086/ws`
5. **Check the connection status**:
   - Extension popup should show "Connected" status
   - Backend logs should show: `✅ Kimi WebBridge extension connected!`

### 4. Verify Connection

Run the connection test:

```bash
cd backend
python test_kimi_connection.py
```

Expected output:
```
✅ Connected to ws://127.0.0.1:10086/ws
✅ Hello message sent
✅ Received response: hello_ack
🎉 SUCCESS! Kimi WebBridge is properly connected!
```

## Troubleshooting

### Issue: Extension shows "Disconnected"

**Solution:**
1. Make sure backend server is running
2. Refresh the LinkedIn page in your browser
3. Click the extension icon and check status
4. Check browser console (F12) for connection errors

### Issue: Backend logs show "Port 10086 already in use"

**Solution:**
This is actually OK! It means the server is already running. The backend handles this gracefully.

### Issue: "Another client tried to connect. Refusing."

**Solution:**
Only ONE browser can be connected at a time. Close other browsers or restart the backend.

### Issue: Extension connects but posting fails

**Solution:**
1. Make sure you're logged into LinkedIn in the browser
2. Try manually posting to verify your session is active
3. Check if LinkedIn is blocking automation (verify in browser console)

## How It Works

1. **Backend starts WebSocket server** on `ws://127.0.0.1:10086/ws`
2. **Extension connects** when you open a browser with LinkedIn
3. **Backend sends commands** like:
   ```json
   {
     "type": "tool_call",
     "requestId": "abc123",
     "payload": {
       "name": "navigate",
       "args": {"url": "https://www.linkedin.com/feed/"}
     }
   }
   ```
4. **Extension executes** the command in the real browser
5. **Extension responds** with the result:
   ```json
   {
     "type": "tool_result",
     "responseToRequestId": "abc123",
     "payload": {"data": {...}}
   }
   ```

## Supported Commands

### navigate
Navigate to a URL
```python
await kimi_server.execute_tool("navigate", {"url": "https://www.linkedin.com/feed/"})
```

### click
Click an element
```python
await kimi_server.execute_tool("click", {"selector": "button.post-button"})
```

### fill
Fill a text field
```python
await kimi_server.execute_tool("fill", {
    "selector": "div.ql-editor",
    "value": "Post content here"
})
```

### evaluate
Execute JavaScript and get the result
```python
result = await kimi_server.execute_tool("evaluate", {
    "code": "document.querySelector('.profile-name').innerText"
})
```

### snapshot
Take a screenshot
```python
result = await kimi_server.execute_tool("snapshot", {})
```

## Security Notes

⚠️ **IMPORTANT:**
- Kimi WebBridge has FULL ACCESS to your browser session
- Only use on your local machine for personal projects
- Never expose the WebSocket server (port 10086) to the internet
- The backend runs on `127.0.0.1` (localhost only) for security

## Testing

### Quick Test
```bash
cd backend
python test_kimi_connection.py
```

### Full E2E Test
```bash
cd backend
python test_complete_agent.py
```

This will:
1. ✅ Check Kimi connection
2. ✅ Fetch your LinkedIn profile
3. ✅ Analyze your feed
4. ✅ Generate a viral post
5. ✅ Post to your LinkedIn account

## Environment Variables

In your `.env` file:

```bash
# Browser Provider
BROWSER_PROVIDER=kimi_webbridge  # Use Kimi as primary
AUTH_MODE=browser

# Playwright is auto-configured as fallback if Kimi fails
```

## Benefits vs Playwright

| Feature | Kimi WebBridge | Playwright |
|---------|----------------|------------|
| Setup | Install extension once | Configure each time |
| Credentials | Uses your login | Needs credentials |
| Detection Risk | Very Low (real browser) | Medium-High |
| Session Management | Automatic | Manual |
| LinkedIn Login | Already logged in | Automated login |
| Multi-factor Auth | Works seamlessly | Requires manual intervention |

## Next Steps

1. ✅ Install extension
2. ✅ Start backend
3. ✅ Connect extension
4. ✅ Run tests
5. 🚀 Start using your LinkedIn AI Agent!

---

**Need Help?**
- Check backend logs for connection status
- Check browser console (F12) for extension errors
- Ensure you're logged into LinkedIn before connecting
- Try refreshing the LinkedIn page if connection fails
