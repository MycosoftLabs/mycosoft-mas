# MYCA Intention API

**Component**: Tracks user interactions and search context  
**Status**: Implemented

## Location

- mycosoft_mas/core/routers/intention_api.py
- Prefix: /api/myca/intention

## Endpoints

- POST /api/myca/intention - Record user interaction
- GET /api/myca/intention/session_id - Get session intentions
- GET /api/myca/intention/session_id/suggestions - Get suggestions

## Persistence

- Redis when available, key prefix myca:intention:
- In-memory fallback when Redis unavailable
- TTL: 7 days, max 100 events per session

## Event Types

search, chat, widget_focus, notepad_add
