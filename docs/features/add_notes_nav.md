# Feature: Notes Navigation Item

## 1. Goal
Add a dedicated "Notes" navigation item to the left sidebar in the Gantry application. This item should be placed above the "Manage Workspaces" item and include a relevant icon.

## 2. Requirements
- **Location**: Left Sidebar, inside the "My Stuff" or general tools section (specifically requested "above Manage Workspaces").
- **Icon**: Use existing `fileText` icon or similar standard icon.
- **Link**: Navigate to `/notes`.
- **Styling**: Match existing sidebar items (hover effects, cursor pointer).

## 3. Implementation Details
- **File**: `public/script.js`
- **Component**: `Nebulus.Templates.getSidebar`
- **Change**: Insert the following HTML structure before the Workspace nav item:
  ```html
  <div class="nav-item" onclick="window.location.href='/notes'">
      <div class="nav-icon">${Nebulus.Icons.fileText}</div>
      <span class="nav-label">Notes</span>
  </div>
  ```

## 4. Verification
- **Visual**: Confirm "Notes" item appears above "Manage Workspaces".
- **Functional**: Click "Notes" -> Browser URL changes to `/notes` -> Notes page loads.
