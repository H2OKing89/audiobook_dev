# Template Assets Documentation

## External Image Dependencies

The following templates use external image hosting:

### Current Dependencies

- **templates/index.html** (line 29): `https://ptpimg.me/v7nz0u.png` - Mascot banner image
- **templates/success.html** (line 56): `https://ptpimg.me/l7pkv0.png` - Celebration mascot image

### Reliability Concerns

The current images are hosted on `ptpimg.me`, an external third-party service. This creates potential issues:

1. **Availability**: External service may experience downtime
2. **Performance**: Loading times depend on external server response
3. **Privacy**: Requests leak user IP addresses to third-party
4. **Security**: No control over hosted content (could be replaced)

### Recommended Solutions

#### Option 1: Self-Host Assets (Recommended)

1. Download images from current URLs
2. Place in `static/images/` directory
3. Update template references:
   - `https://ptpimg.me/v7nz0u.png` → `/static/images/mascot-banner.png`
   - `https://ptpimg.me/l7pkv0.png` → `/static/images/celebration-mascot.png`

#### Option 2: Use CDN

1. Upload images to reliable CDN (Cloudflare, AWS CloudFront, etc.)
2. Update template URLs to CDN paths
3. Configure proper caching headers

#### Option 3: Inline SVG

Convert raster images to SVG format and inline them directly in templates for maximum reliability and performance.

### Implementation Status

⚠️ **Action Required**: External image hosting is currently in use. For production deployments, implement one of the recommended solutions above.

### Migration Checklist

- [ ] Download current images from ptpimg.me
- [ ] Create `static/images/` directory
- [ ] Save images with descriptive names
- [ ] Update [templates/index.html](../templates/index.html#L29)
- [ ] Update [templates/success.html](../templates/success.html#L56)
- [ ] Test image loading locally
- [ ] Verify images display correctly
- [ ] Remove this documentation file or update status
