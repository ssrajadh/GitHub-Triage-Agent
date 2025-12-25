# GitHub Triage Agent - Frontend

Mission Control Dashboard for the GitHub Triage Agent.

## Features

- **Live Issue Feed**: Real-time updates via WebSocket
- **Side-by-Side Diff Viewer**: Compare original issue with agent's draft
- **Action Center**: Approve, edit, or reject AI-generated responses
- **Context Display**: View retrieved documentation chunks
- **Auto-Reconnection**: Resilient WebSocket with exponential backoff

## Tech Stack

- React 18 + TypeScript
- Vite (Build tool)
- TailwindCSS (Styling)
- Axios (HTTP client)
- WebSocket (Real-time updates)
- React Markdown (Markdown rendering)

## Setup

### Prerequisites
- Node.js 18+ and npm/yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── Header.tsx
│   │   ├── IssueFeed.tsx
│   │   ├── DiffViewer.tsx
│   │   └── ActionPanel.tsx
│   ├── hooks/           # Custom React hooks
│   │   └── useWebSocket.ts
│   ├── services/        # API services
│   │   └── api.ts
│   ├── types/           # TypeScript types
│   │   └── index.ts
│   ├── styles/          # Global styles
│   │   └── index.css
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
├── public/              # Static assets
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Key Components

### IssueFeed
Displays a live feed of incoming issues with:
- Classification badges (BUG, FEATURE, QUESTION)
- Processing status
- Time since creation
- Click to select

### DiffViewer
Split-pane view showing:
- Original GitHub issue (left)
- Agent's draft response (right)
- Retrieved context chunks

### ActionPanel
Control center with:
- Approve button (posts to GitHub)
- Edit mode (modify before approval)
- Reject button
- Metadata display

### useWebSocket Hook
Custom hook managing:
- WebSocket connection
- Auto-reconnection with exponential backoff
- State updates
- Error handling

## Development

```bash
# Run dev server
npm run dev

# Type checking
npm run lint

# Build
npm run build
```

## Customization

### Styling
Edit `tailwind.config.js` to customize colors, spacing, etc.

### API Endpoints
Modify `src/services/api.ts` to add/change endpoints.

### WebSocket URL
Update `VITE_WS_URL` in `.env` file.

## Troubleshooting

### WebSocket won't connect
- Ensure backend is running on port 8000
- Check firewall settings
- Verify `VITE_WS_URL` in `.env`

### Hot reload not working
- Restart dev server
- Clear browser cache
- Check for TypeScript errors

### Build fails
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Ensure Node.js version is 18+
