# MYCAFloatingButton

**Component**: Floating Brain icon that opens MYCA chat sheet  
**Status**: Implemented

## Location

- `WEBSITE/website/components/myca/MYCAFloatingButton.tsx`

## Props

- `title`, `className` – optional

## Behavior

- Renders floating button (Brain icon)
- Click opens Sheet with embedded `MYCAChatWidget`
- `getContextText` provides page context to chat

## Used In

- `app/natureos/layout.tsx` – NatureOS layout
- `app/scientific/layout.tsx` – Scientific layout
- `app/dashboard/page.tsx` – Dashboard
- `app/admin/voice-health/page.tsx` – Voice diagnostics

## Integration

- Wraps `MYCAChatWidget` with `showHeader={false}`
- Position: bottom-right by default
