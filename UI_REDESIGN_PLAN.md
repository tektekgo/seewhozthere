# SeeWhozThere UI Redesign Plan

## Design Goals
- Modern, professional app-style interface
- Clean navigation with logo and menu
- Responsive design (desktop, tablet, mobile)
- Dark mode support
- Smooth animations and transitions
- Enhanced user experience

## New Features to Add

### 1. Navigation Header
- Logo/brand name on left
- Navigation menu: Dashboard | History | Settings
- Stats summary in header (total visitors, today's count)
- Dark mode toggle

### 2. Stats Dashboard Section
- Total Visitors (all time)
- Today's Visitors
- Active Cameras
- Recent Activity count

### 3. Enhanced Visitor Cards
- Larger profile images with hover effects
- Status badges (New, Frequent, Unknown)
- Quick action buttons (View History, Identify)
- Last seen time with relative format ("2 hours ago")
- Confidence score visualization

### 4. Filters & Search
- Filter by: All | Known | Unknown
- Search by name
- Date range selector

### 5. Unknown Visitors Section
- Separate section for unidentified faces
- "Identify" button to assign names
- Batch identification

### 6. Footer
- Copyright info
- Privacy statement
- Version number
- GitHub link

## Technology Stack
- **Tailwind CSS** via CDN (no build step needed)
- **Alpine.js** for interactivity (lightweight, no build step)
- **Font Awesome** for icons
- Keep FastAPI + Jinja2 backend (no changes needed)

## Color Scheme
- Primary: Blue (#3B82F6)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- Dark mode: Gray scale (#1F2937, #111827)

## Layout Structure
```
┌─────────────────────────────────────────┐
│ Header (Logo | Nav | Stats | Dark Mode)│
├─────────────────────────────────────────┤
│ Stats Dashboard (4 cards)               │
├─────────────────────────────────────────┤
│ Filters & Search Bar                    │
├─────────────────────────────────────────┤
│ Visitor Grid (3-4 columns responsive)   │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐           │
│ │Card│ │Card│ │Card│ │Card│           │
│ └────┘ └────┘ └────┘ └────┘           │
├─────────────────────────────────────────┤
│ Unknown Visitors Section                │
├─────────────────────────────────────────┤
│ Footer                                  │
└─────────────────────────────────────────┘
```

## Implementation Steps
1. Add Tailwind CSS CDN to HTML
2. Add Alpine.js for client-side interactivity
3. Rebuild header with navigation
4. Create stats dashboard component
5. Redesign visitor cards with Tailwind
6. Add filters and search (frontend only for now)
7. Create unknown visitors section
8. Update footer
9. Add dark mode toggle with localStorage
10. Test responsive design
