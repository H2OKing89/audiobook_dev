# 🌐 Web Interface Guide

The Audiobook Automation System includes a modern web interface for managing audiobook requests, approvals, and monitoring system status.

## 🚀 Accessing the Web Interface

Once the system is running, access the web interface at:
```
http://localhost:8080
```

Or if configured for external access:
```
http://your-server-ip:8080
```

## 📋 Main Interface Features

### 🎯 Dashboard
- **Request Queue** - View pending audiobook requests
- **Recent Activity** - See approved/rejected requests
- **System Status** - Monitor system health and performance
- **Statistics** - Request processing metrics

### ✅ Request Approval Interface

The approval interface features a modern, cyberpunk-inspired design:

#### 📚 Book Information Panel
- **Cover Art** - High-quality book cover display
- **Metadata** - Title, author, narrator, publisher
- **Series Information** - Series name and book number
- **Description** - Book synopsis and details
- **Technical Info** - File format, size, quality

#### 🔍 Source Information
- **Torrent Details** - Seeders, leechers, size
- **MAM URL** - Direct link to source page
- **ASIN** - Amazon identifier (if available)
- **Categories** - Genre and classification tags

#### ⚡ Action Buttons
- **✅ Approve** - Approve the audiobook request
- **❌ Reject** - Reject with optional reason
- **🏠 Home** - Return to dashboard
- **🔄 Refresh** - Update request information

### ⌨️ Keyboard Shortcuts

The interface supports keyboard shortcuts for efficient navigation:

- **A** - Approve current request
- **R** - Reject current request  
- **H** - Go to home/dashboard
- **ESC** - Cancel current action
- **Enter** - Confirm dialog actions
- **Space** - Refresh current page

### 📱 Responsive Design

The interface is fully responsive and works on:
- **Desktop** - Full-featured interface
- **Tablet** - Optimized layout with touch controls
- **Mobile** - Compact interface for on-the-go approvals

## 🎨 Interface Themes

### Cyberpunk Theme (Default)
- **Terminal-inspired design** with scanning animations
- **Blue/green color scheme** with high contrast
- **Monospace fonts** for technical feel
- **Interactive elements** with hover effects

### Accessibility Features
- **High contrast** text and backgrounds
- **Keyboard navigation** support
- **Screen reader** compatible
- **Focus indicators** for navigation

## 🔐 Security Features

### Authentication
- **Token-based authentication** for webhook endpoints
- **CSRF protection** on all forms
- **Rate limiting** to prevent abuse

### Input Validation
- **Sanitized inputs** prevent XSS attacks
- **Request size limits** prevent DoS
- **Path traversal protection** secures file access

## 📊 Monitoring & Logs

### Request Logs
- **Approval History** - Track all approval/rejection decisions
- **Processing Time** - Monitor request processing speed
- **Error Logs** - View system errors and issues

### System Status
- **Queue Length** - Number of pending requests
- **Processing Rate** - Requests processed per hour
- **Success Rate** - Percentage of successful requests
- **API Health** - Status of external API connections

## 🛠️ Admin Features

### Configuration Management
- **Rate Limit Settings** - Adjust API call frequency
- **Notification Settings** - Configure Discord/Pushover alerts
- **Source Priorities** - Set metadata source preferences

### Maintenance
- **Database Cleanup** - Remove old processed requests
- **Log Rotation** - Manage log file sizes
- **Cache Management** - Clear metadata caches

## 🎯 Usage Tips

### Efficient Approval Workflow
1. **Use keyboard shortcuts** for faster navigation
2. **Review metadata quality** before approving
3. **Check series information** for completeness
4. **Verify source quality** (seeders, file format)

### Troubleshooting Interface Issues
- **Refresh the page** if interface becomes unresponsive
- **Check browser console** for JavaScript errors
- **Verify token authentication** if requests fail
- **Clear browser cache** if styling issues occur

## 📱 Mobile Usage

### Touch Interface
- **Swipe gestures** for navigation
- **Touch-friendly buttons** with adequate spacing
- **Pinch-to-zoom** for detailed information
- **Long-press menus** for additional options

### Offline Functionality
- **Cached interface** works during brief network interruptions
- **Queue synchronization** when connection restored
- **Local storage** preserves form data

## 🔧 Customization

### Custom Themes
The interface supports custom CSS themes:
```css
/* Add to static/css/custom.css */
:root {
  --primary-color: #your-color;
  --background-color: #your-bg;
}
```

### Custom Shortcuts
Keyboard shortcuts can be customized in the configuration:
```yaml
interface:
  shortcuts:
    approve: "a"
    reject: "r"
    home: "h"
```

## 📋 Interface Checklist

- [ ] Web interface accessible at configured port
- [ ] Authentication working with webhook tokens
- [ ] Approval/rejection functionality tested
- [ ] Keyboard shortcuts working
- [ ] Mobile interface responsive
- [ ] Notifications configured (if desired)
- [ ] Logs accessible and readable
