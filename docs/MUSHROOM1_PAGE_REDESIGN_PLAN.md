# Mushroom 1 Page Redesign Plan

**Date**: 2026-01-21  
**Status**: Planning Phase

## Overview
Comprehensive redesign of `/devices/mushroom-1` page with content reorganization, new messaging, and enhanced interactive features.

---

## 1. HERO SECTION TEXT CHANGES

### Current → New
- **Badge**: `"Pre-Order Now - $2,000"` → `"Environmental drone"`
- **Main Title**: `"The world's first ground-based fungal intelligence station"` → `"The world's first real droid"`
- **Subtitle (green text)**: `"Giving nature a voice"` → `"Giving nature its own computer"`

**Location**: `mushroom1-details.tsx` lines ~225-250

---

## 2. PRE-ORDER BUTTON → MODAL

### Current Behavior
- Button links to shopping/pre-order (placeholder)

### New Behavior
- Opens extensive pre-order instruction modal/page with:
  - **Device diagram** (visual representation)
  - **What you get** section (components, accessories, included items)
  - **All features and details** (comprehensive feature list)
  - **Deployment timeline**: Extensive explanation that device won't be deployed until **mid-to-end of 2026**

**Implementation**: Create new `PreOrderModal` component with comprehensive information layout

---

## 3. CONTENT REORGANIZATION

### Current Order (top to bottom):
1. Hero Section
2. Why Mushroom 1 Exists
3. Photo Gallery Carousel ("In the Wild")
4. Use Cases
5. YouTube Videos
6. Sensor Capabilities ("Advanced Sensor Suite")
7. Blueprint Section
8. Mesh Network
9. Technical Specifications
10. CTA Section

### New Order:
1. Hero Section
2. Why Mushroom 1 Exists
3. **Advanced Sensor Suite** ⬆️ (MOVED UP)
4. Photo Gallery Carousel ("In the Wild") ⬇️ (MOVED DOWN)
5. Use Cases
6. YouTube Videos
7. Blueprint Section
8. Mesh Network
9. Technical Specifications
10. CTA Section

**Reason**: Too much video/pictures before detail - technical info should come earlier

---

## 4. YOUTUBE VIDEO THUMBNAILS

### Current Issue:
- Only first video has thumbnail
- Other 2 videos missing thumbnails

### Fix:
- Use YouTube thumbnail API for all 3 videos:
  - Format: `https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg`
  - Verify all 3 videos have thumbnails available

**Location**: Lines ~588-614 in `mushroom1-details.tsx`

---

## 5. TECHNICAL DETAILS SECTION ENHANCEMENTS

### "Download Full Specifications"
- Create standalone PDF/document
- Button downloads: `Mushroom1_Full_Specifications.pdf`
- **Status**: Document needs to be created (placeholder for now)

### "View CAD Models"
- Needs interactive 3D viewer
- User will provide CAD files
- **Implementation**: 
  - Use Three.js or similar 3D viewer library
  - Placeholder for now until files provided
  - Should show device in 3D with rotation/zoom

**Location**: Lines ~921-930

---

## 6. INSIDE MUSHROOM ONE SECTION REDESIGN

### Current Layout:
- Blueprint/image centered
- Component markers with tooltips

### New Layout:
- **RIGHT SIDE**: Blueprint panel (existing, moved to right)
- **LEFT SIDE**: 
  - Series of explanation widgets (high detail) for each component
  - Each widget should have:
    - Component name
    - Detailed description
    - Technical specs
    - Function explanation
  - Small video windows explaining each part (if videos available)

**Layout Change**:
- Current: Centered blueprint
- New: Two-column layout (explanations left, blueprint right)

**Location**: Lines ~692-801 (Blueprint Section)

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Text Changes (Quick)
- [ ] Update hero section badge text
- [ ] Update main title
- [ ] Update subtitle

### Phase 2: Reorganization (Medium)
- [ ] Move "Advanced Sensor Suite" above "In the Wild"
- [ ] Update section ordering

### Phase 3: Pre-Order Modal (Complex)
- [ ] Create `PreOrderModal` component
- [ ] Design comprehensive layout
- [ ] Add device diagram
- [ ] Add "What you get" section
- [ ] Add features/details section
- [ ] Add deployment timeline explanation
- [ ] Wire up pre-order button to open modal

### Phase 4: YouTube Thumbnails (Quick)
- [ ] Verify all 3 video IDs have thumbnails
- [ ] Ensure thumbnail URLs work

### Phase 5: Technical Details (Medium)
- [ ] Create placeholder for "Download Full Specifications" button
- [ ] Create placeholder for "View CAD Models" 3D viewer
- [ ] Plan Three.js integration for CAD viewer

### Phase 6: Blueprint Section Redesign (Complex)
- [ ] Change layout to two-column (explanations left, blueprint right)
- [ ] Create detailed widget components for each device component
- [ ] Add video placeholders for component explanations
- [ ] Maintain interactivity with blueprint markers

---

## FILES TO MODIFY

1. `components/devices/mushroom1-details.tsx` - Main component
2. `components/devices/pre-order-modal.tsx` - New component (to be created)
3. `components/devices/component-explanation-widget.tsx` - New component (to be created)
4. `components/devices/cad-viewer.tsx` - New component (to be created, placeholder)

---

## NOTES

- **CAD Files**: User will provide files later for 3D viewer
- **Video Assets**: Component explanation videos may need to be created/added
- **PDF Generation**: Specifications document needs to be created
- **Deployment Timeline**: Emphasize mid-to-end 2026 (not Q2 2026)

---

## QUESTIONS FOR USER

1. Do you have component explanation videos ready, or should we use placeholders?
2. When will CAD files be available for the 3D viewer?
3. Do you have the specifications PDF ready, or should we create it?
4. Should the pre-order modal be a full-page modal or a smaller centered modal?
