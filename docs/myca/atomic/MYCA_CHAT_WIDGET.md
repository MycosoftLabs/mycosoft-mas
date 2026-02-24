# MYCAChatWidget

**Component**: Chat UI for MYCA conversations  
**Status**: Implemented

## Location

- `WEBSITE/website/components/myca/MYCAChatWidget.tsx`

## Props

- `className`, `showHeader`, `getContextText` – optional

## Behavior

- Uses `useMYCA()` for messages, sendMessage, consciousness
- Sends to MAS via `/api/myca/chat` (proxied from search/ai) or direct MAS
- Supports streaming via `/api/search/ai/stream` when available
- Renders `nlqData`, `nlqActions` from assistant messages

## Used In

- `components/myca/MYCAFloatingButton.tsx` – embedded in sheet
- `app/natureos/ai-studio/page.tsx` – standalone chat
- Dashboard, scientific layout – via MYCAFloatingButton

## MAS Endpoints

- Website proxies to `MAS_API_URL/api/myca/chat`
- Stream: `MAS_API_URL/voice/brain/stream`
