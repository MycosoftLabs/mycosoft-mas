# MYCAProvider

**Component**: React context for MYCA session, conversation, and actions  
**Status**: Implemented

## Location

- `WEBSITE/website/contexts/myca-context.tsx`

## Key Exports

- `MYCAProvider` – wraps children with MYCA context
- `useMYCA()` – hook for session, messages, sendMessage, executeSearchAction
- `MYCAMessage`, `MYCASearchAction`, `MYCAConsciousnessState` – types

## Storage Keys (localStorage)

- `myca_session_id:{userId|anon}`
- `myca_conversation_id:{userId|anon}`
- `myca_messages:{userId|anon}`

## Key Methods

| Method | Purpose |
|--------|---------|
| `sendMessage(text, options)` | Send message to MAS, append to messages |
| `executeSearchAction(action)` | Dispatch `myca-search-action` CustomEvent |
| `restoreFromMAS()` | Load conversation from MAS |
| `syncToMAS()` | Save conversation to MAS |

## Search Actions

Types: `search`, `focus_widget`, `expand_widget`, `add_to_notepad`, `clear_search`  
Widgets: `species`, `chemistry`, `genetics`, `research`, `ai`

## Used By

- `app/search/page.tsx` – wraps FluidSearchCanvas
- `components/myca/MYCAFloatingButton.tsx` – via useMYCA
- `components/myca/MYCAChatWidget.tsx` – via useMYCA
