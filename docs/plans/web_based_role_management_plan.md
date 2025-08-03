# Web-Based User Role Management Implementation Plan

## Overview
Create a secure, admin-only web interface for managing user roles and permissions without requiring CLI access or manual database operations.

## Current System Analysis

ThyWill has a sophisticated role-based permission system with:

### Existing Models
- **User**: Core user model with role checking methods (`has_role()`, `has_permission()`, `get_roles()`)
- **Role**: Defines permission levels with JSON permissions field
- **UserRole**: Many-to-many relationship with expiration support

### Current CLI Tools
- `app_helpers/cli/role_management.py` - Complete CLI role management
- Supports grant/revoke for any role, not just admin
- Has backward compatibility with legacy admin system

### Existing Admin Routes Structure
- `app_helpers/routes/admin/` - Modular admin route organization
- `app_helpers/routes/admin/user_management.py` - User management functionality
- Admin authentication already implemented

## Goals
- **Ease of Use**: Intuitive web interface for role management
- **Security**: Admin-only access with proper authentication
- **Comprehensive**: Support for all roles, not just admin
- **Safety**: Role assignment validation and audit logging
- **Flexibility**: Support for role expiration and bulk operations

## Architecture Design

### Core Components

#### 1. Role Management Service (`app_helpers/services/role_management_service.py`)
```python
class RoleManagementService:
    """Handles role operations with validation and audit logging."""
    
    def get_all_users_with_roles(self) -> Dict[str, UserRoleInfo]
    def get_all_roles(self) -> List[RoleInfo]
    def grant_role(self, user_id: str, role_name: str, granted_by: str, expires_at: Optional[datetime]) -> Result
    def revoke_role(self, user_id: str, role_name: str, revoked_by: str) -> Result
    def create_role(self, name: str, description: str, permissions: List[str], created_by: str) -> Result
    def bulk_role_operations(self, operations: List[RoleOperation]) -> BulkResult
    def get_role_audit_log(self, limit: int = 100) -> List[AuditEntry]
```

#### 2. Admin Routes (`app_helpers/routes/admin/role_management.py`)
```python
@router.get("/roles")
async def role_management_page()

@router.get("/api/users-roles")
async def get_users_with_roles()

@router.get("/api/roles")
async def get_all_roles()

@router.post("/api/roles/grant")
async def grant_user_role()

@router.post("/api/roles/revoke")
async def revoke_user_role()

@router.post("/api/roles/create")
async def create_new_role()

@router.get("/api/roles/audit")
async def get_role_audit_log()
```

#### 3. Frontend Interface (`templates/admin_roles.html`)
- User role matrix display
- Role management controls
- Bulk operations interface
- Audit log viewer

## Implementation Plan

### Phase 1: Core Service Layer

#### Step 1.1: Role Management Service
Create `app_helpers/services/role_management_service.py`:

```python
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime
from sqlmodel import Session, select
from models import engine, User, Role, UserRole

@dataclass
class UserRoleInfo:
    user: User
    roles: List[Dict[str, any]]  # Role info with expiration, granted_by, etc.

@dataclass
class RoleInfo:
    role: Role
    permissions: List[str]
    user_count: int
    is_system_role: bool

@dataclass
class RoleOperation:
    operation: str  # 'grant' or 'revoke'
    user_id: str
    role_name: str
    expires_at: Optional[datetime] = None

@dataclass
class AuditEntry:
    timestamp: datetime
    action: str
    user_id: str
    role_name: str
    performed_by: str
    details: str

class RoleManagementService:
    def __init__(self):
        self.engine = engine
    
    def get_all_users_with_roles(self) -> List[UserRoleInfo]:
        """Get all users with their assigned roles."""
        with Session(self.engine) as session:
            # Get all users
            users = list(session.exec(select(User)))
            
            user_role_info = []
            for user in users:
                # Get user's roles with metadata
                stmt = (select(Role, UserRole)
                       .join(UserRole, Role.id == UserRole.role_id)
                       .where(UserRole.user_id == user.display_name))
                
                role_assignments = session.exec(stmt).all()
                
                roles = []
                for role, user_role in role_assignments:
                    roles.append({
                        'name': role.name,
                        'description': role.description,
                        'granted_at': user_role.granted_at,
                        'granted_by': user_role.granted_by,
                        'expires_at': user_role.expires_at,
                        'is_active': user_role.expires_at is None or user_role.expires_at > datetime.utcnow()
                    })
                
                user_role_info.append(UserRoleInfo(user=user, roles=roles))
            
            return user_role_info
    
    def get_all_roles(self) -> List[RoleInfo]:
        """Get all available roles with metadata."""
        with Session(self.engine) as session:
            roles = list(session.exec(select(Role)))
            
            role_info = []
            for role in roles:
                # Count users with this role
                user_count_stmt = select(UserRole).where(UserRole.role_id == role.id)
                user_count = len(list(session.exec(user_count_stmt)))
                
                # Parse permissions
                import json
                try:
                    permissions = json.loads(role.permissions)
                except json.JSONDecodeError:
                    permissions = []
                
                role_info.append(RoleInfo(
                    role=role,
                    permissions=permissions,
                    user_count=user_count,
                    is_system_role=role.is_system_role
                ))
            
            return role_info
    
    def grant_role(self, user_id: str, role_name: str, granted_by: str, 
                   expires_at: Optional[datetime] = None) -> bool:
        """Grant a role to a user with audit logging."""
        try:
            with Session(self.engine) as session:
                # Validate user exists  
                user = session.exec(select(User).where(User.display_name == user_id)).first()
                if not user:
                    return False
                
                # Validate role exists
                role = session.exec(select(Role).where(Role.name == role_name)).first()
                if not role:
                    return False
                
                # Check if user already has this role
                existing = session.exec(select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id
                )).first()
                
                if existing:
                    # Update expiration if different
                    if existing.expires_at != expires_at:
                        existing.expires_at = expires_at
                        session.commit()
                    return True
                
                # Create new role assignment
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    granted_by=granted_by,
                    granted_at=datetime.utcnow(),
                    expires_at=expires_at
                )
                session.add(user_role)
                session.commit()
                
                # Log the action
                self._log_role_action(session, "GRANT", user_id, role_name, granted_by, expires_at)
                
                return True
                
        except Exception as e:
            print(f"Error granting role: {e}")
            return False
    
    def revoke_role(self, user_id: str, role_name: str, revoked_by: str) -> bool:
        """Revoke a role from a user with audit logging."""
        try:
            with Session(self.engine) as session:
                # Get role
                role = session.exec(select(Role).where(Role.name == role_name)).first()
                if not role:
                    return False
                
                # Find and remove role assignment
                user_roles = session.exec(select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id
                )).all()
                
                for user_role in user_roles:
                    session.delete(user_role)
                
                session.commit()
                
                # Log the action
                self._log_role_action(session, "REVOKE", user_id, role_name, revoked_by)
                
                return True
                
        except Exception as e:
            print(f"Error revoking role: {e}")
            return False
    
    def _log_role_action(self, session: Session, action: str, user_id: str, 
                        role_name: str, performed_by: str, expires_at: Optional[datetime] = None):
        """Log role management actions."""
        from app_helpers.services.auth_helpers import log_security_event
        
        details = f"Role '{role_name}' {action.lower()}ed for user '{user_id}'"
        if expires_at:
            details += f" (expires: {expires_at})"
        
        log_security_event(
            session=session,
            event_type=f"ROLE_{action}",
            user_id=performed_by,
            details=details,
            ip_address=None  # Will be filled by route handler
        )
```

### Phase 2: API Endpoints

#### Step 2.1: Role Management Routes
Create `app_helpers/routes/admin/role_management.py`:

```python
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app_helpers.services.auth_helpers import require_full_auth, is_admin
from app_helpers.services.role_management_service import RoleManagementService
from app_helpers.shared_templates import templates

router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])

class RoleGrantRequest(BaseModel):
    user_id: str
    role_name: str
    expires_at: Optional[datetime] = None

class RoleRevokeRequest(BaseModel):
    user_id: str
    role_name: str

class NewRoleRequest(BaseModel):
    name: str
    description: str
    permissions: List[str]

class BulkRoleRequest(BaseModel):
    operations: List[dict]  # List of RoleOperation dicts

async def require_admin_role(request: Request, current_user = Depends(require_full_auth)):
    """Ensure user has admin role for role management operations."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/")
async def role_management_page(request: Request, current_user = Depends(require_admin_role)):
    """Render the role management interface."""
    return templates.TemplateResponse("admin_roles.html", {
        "request": request,
        "current_user": current_user
    })

@router.get("/api/users-roles")
async def get_users_with_roles(current_user = Depends(require_admin_role)):
    """Get all users with their assigned roles."""
    service = RoleManagementService()
    users_roles = service.get_all_users_with_roles()
    
    return {
        "users": [
            {
                "user": {
                    "id": ur.user.display_name,
                    "display_name": ur.user.display_name,
                    "created_at": ur.user.created_at,
                    "is_supporter": ur.user.is_supporter
                },
                "roles": ur.roles
            }
            for ur in users_roles
        ]
    }

@router.get("/api/roles")
async def get_all_roles(current_user = Depends(require_admin_role)):
    """Get all available roles with metadata."""
    service = RoleManagementService()
    roles = service.get_all_roles()
    
    return {
        "roles": [
            {
                "id": r.role.id,
                "name": r.role.name,
                "description": r.role.description,
                "permissions": r.permissions,
                "user_count": r.user_count,
                "is_system_role": r.is_system_role,
                "created_at": r.role.created_at
            }
            for r in roles
        ]
    }

@router.post("/api/grant")
async def grant_user_role(
    request: RoleGrantRequest,
    current_user = Depends(require_admin_role)
):
    """Grant a role to a user."""
    service = RoleManagementService()
    
    success = service.grant_role(
        user_id=request.user_id,
        role_name=request.role_name,
        granted_by=current_user.display_name,
        expires_at=request.expires_at
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to grant role")
    
    return {"success": True, "message": f"Role '{request.role_name}' granted to '{request.user_id}'"}

@router.post("/api/revoke")
async def revoke_user_role(
    request: RoleRevokeRequest,
    current_user = Depends(require_admin_role)
):
    """Revoke a role from a user."""
    service = RoleManagementService()
    
    success = service.revoke_role(
        user_id=request.user_id,
        role_name=request.role_name,
        revoked_by=current_user.display_name
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to revoke role")
    
    return {"success": True, "message": f"Role '{request.role_name}' revoked from '{request.user_id}'"}

@router.post("/api/roles/create")
async def create_new_role(
    request: NewRoleRequest,
    current_user = Depends(require_admin_role)
):
    """Create a new role."""
    # Implementation for creating new roles
    # This would extend the service to support role creation
    return {"success": True, "message": f"Role '{request.name}' created"}

@router.post("/api/bulk")
async def bulk_role_operations(
    request: BulkRoleRequest,
    current_user = Depends(require_admin_role)
):
    """Perform bulk role operations."""
    service = RoleManagementService()
    
    results = []
    for op in request.operations:
        if op["operation"] == "grant":
            success = service.grant_role(
                user_id=op["user_id"],
                role_name=op["role_name"],
                granted_by=current_user.display_name,
                expires_at=op.get("expires_at")
            )
        elif op["operation"] == "revoke":
            success = service.revoke_role(
                user_id=op["user_id"],
                role_name=op["role_name"],
                revoked_by=current_user.display_name
            )
        else:
            success = False
        
        results.append({
            "operation": op,
            "success": success
        })
    
    return {"results": results}

@router.get("/api/audit")
async def get_role_audit_log(
    limit: int = 100,
    current_user = Depends(require_admin_role)
):
    """Get role management audit log."""
    # Implementation would query security log for role-related events
    return {"audit_entries": []}
```

### Phase 3: User Interface

#### Step 3.1: Admin Roles Template
Create `templates/admin_roles.html`:

```html
{% extends "base.html" %}
{% block title %}Role Management{% endblock %}

{% block content %}
<div class="role-management-container">
    <header class="role-header">
        <h1>👥 User Role Management</h1>
        <div class="role-actions">
            <button id="bulk-operations" class="btn-secondary">Bulk Operations</button>
            <button id="create-role" class="btn-primary">Create New Role</button>
            <button id="refresh-data" class="btn-secondary">🔄 Refresh</button>
        </div>
    </header>

    <!-- Role Summary Cards -->
    <div class="role-summary">
        <div class="summary-card">
            <h3>Total Users</h3>
            <span class="count" id="total-users">-</span>
        </div>
        <div class="summary-card">
            <h3>Available Roles</h3>
            <span class="count" id="total-roles">-</span>
        </div>
        <div class="summary-card">
            <h3>Admin Users</h3>
            <span class="count" id="admin-count">-</span>
        </div>
    </div>

    <!-- Role Management Tabs -->
    <div class="role-tabs">
        <button class="tab-button active" data-tab="user-roles">👤 User Roles</button>
        <button class="tab-button" data-tab="role-definitions">🎭 Role Definitions</button>
        <button class="tab-button" data-tab="audit-log">📋 Audit Log</button>
    </div>

    <!-- User Roles Tab -->
    <div class="tab-content active" id="user-roles">
        <div class="user-role-controls">
            <input type="text" id="user-search" placeholder="Search users..." />
            <select id="role-filter">
                <option value="">All Roles</option>
            </select>
            <label>
                <input type="checkbox" id="show-expired" />
                Show Expired Roles
            </label>
        </div>

        <div class="user-role-matrix">
            <table class="role-table">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Supporter Status</th>
                        <th>Roles</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="user-roles-body">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Role Definitions Tab -->
    <div class="tab-content" id="role-definitions">
        <div class="roles-grid" id="roles-grid">
            <!-- Populated by JavaScript -->
        </div>
    </div>

    <!-- Audit Log Tab -->
    <div class="tab-content" id="audit-log">
        <div class="audit-controls">
            <select id="audit-filter">
                <option value="">All Actions</option>
                <option value="GRANT">Grants</option>
                <option value="REVOKE">Revokes</option>
            </select>
            <input type="date" id="audit-date-from" />
            <input type="date" id="audit-date-to" />
        </div>
        <div class="audit-log-list" id="audit-log-list">
            <!-- Populated by JavaScript -->
        </div>
    </div>
</div>

<!-- Role Assignment Modal -->
<div class="modal" id="role-modal">
    <div class="modal-content">
        <h3>Assign Role</h3>
        <form id="role-form">
            <div class="form-group">
                <label for="modal-user">User:</label>
                <input type="text" id="modal-user" readonly />
            </div>
            <div class="form-group">
                <label for="modal-role">Role:</label>
                <select id="modal-role" required>
                    <!-- Populated by JavaScript -->
                </select>
            </div>
            <div class="form-group">
                <label for="modal-expires">Expires At (optional):</label>
                <input type="datetime-local" id="modal-expires" />
            </div>
            <div class="form-actions">
                <button type="submit" class="btn-primary">Assign Role</button>
                <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            </div>
        </form>
    </div>
</div>

<!-- Bulk Operations Modal -->
<div class="modal" id="bulk-modal">
    <div class="modal-content">
        <h3>Bulk Role Operations</h3>
        <div class="bulk-operations">
            <div class="bulk-controls">
                <select id="bulk-role">
                    <option value="">Select Role</option>
                </select>
                <button id="bulk-grant" class="btn-primary">Grant to Selected</button>
                <button id="bulk-revoke" class="btn-warning">Revoke from Selected</button>
            </div>
            <div class="bulk-users">
                <h4>Select Users:</h4>
                <div id="bulk-user-list">
                    <!-- Populated by JavaScript -->
                </div>
            </div>
        </div>
        <div class="form-actions">
            <button type="button" class="btn-secondary" onclick="closeBulkModal()">Close</button>
        </div>
    </div>
</div>

<script src="/static/js/admin-roles.js"></script>
{% endblock %}
```

#### Step 3.2: Frontend JavaScript
Create `static/js/admin-roles.js`:

```javascript
class RoleManager {
    constructor() {
        this.users = [];
        this.roles = [];
        this.selectedUsers = new Set();
        this.init();
    }

    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.renderUserRoles();
        this.renderRoleDefinitions();
        this.updateSummary();
    }

    async loadData() {
        try {
            // Load users with roles
            const usersResponse = await fetch('/admin/roles/api/users-roles');
            const usersData = await usersResponse.json();
            this.users = usersData.users;

            // Load available roles
            const rolesResponse = await fetch('/admin/roles/api/roles');
            const rolesData = await rolesResponse.json();
            this.roles = rolesData.roles;

        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading role data');
        }
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Search and filters
        document.getElementById('user-search').addEventListener('input', (e) => {
            this.filterUsers(e.target.value);
        });

        document.getElementById('role-filter').addEventListener('change', (e) => {
            this.filterByRole(e.target.value);
        });

        // Refresh data
        document.getElementById('refresh-data').addEventListener('click', () => {
            this.init();
        });

        // Modal form submission
        document.getElementById('role-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.assignRole();
        });

        // Bulk operations
        document.getElementById('bulk-operations').addEventListener('click', () => {
            this.openBulkModal();
        });
    }

    switchTab(tabName) {
        // Remove active class from all tabs and content
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // Add active class to selected tab and content
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');

        // Load specific content
        if (tabName === 'audit-log') {
            this.loadAuditLog();
        }
    }

    renderUserRoles() {
        const tbody = document.getElementById('user-roles-body');
        tbody.innerHTML = '';

        this.users.forEach(userRole => {
            const row = this.createUserRoleRow(userRole);
            tbody.appendChild(row);
        });
    }

    createUserRoleRow(userRole) {
        const row = document.createElement('tr');
        const user = userRole.user;
        const roles = userRole.roles;

        // Create role badges
        const roleBadges = roles.map(role => {
            const isExpired = role.expires_at && new Date(role.expires_at) < new Date();
            const badgeClass = isExpired ? 'role-badge expired' : 'role-badge';
            const expiryText = role.expires_at ? ` (expires ${new Date(role.expires_at).toLocaleDateString()})` : '';
            
            return `<span class="${badgeClass}" title="Granted by ${role.granted_by || 'System'}">${role.name}${expiryText}</span>`;
        }).join(' ');

        row.innerHTML = `
            <td>
                <div class="user-info">
                    <strong>${user.display_name}</strong>
                    <small>Created: ${new Date(user.created_at).toLocaleDateString()}</small>
                </div>
            </td>
            <td>
                ${user.is_supporter ? '<span class="supporter-badge">♥ Supporter</span>' : '-'}
            </td>
            <td class="roles-cell">
                ${roleBadges || '<em>No roles assigned</em>'}
            </td>
            <td class="actions-cell">
                <button class="btn-small btn-primary" onclick="roleManager.openRoleModal('${user.id}')">
                    + Assign Role
                </button>
                ${roles.length > 0 ? `<button class="btn-small btn-warning" onclick="roleManager.manageUserRoles('${user.id}')">Manage</button>` : ''}
            </td>
        `;

        return row;
    }

    renderRoleDefinitions() {
        const grid = document.getElementById('roles-grid');
        grid.innerHTML = '';

        this.roles.forEach(role => {
            const card = this.createRoleCard(role);
            grid.appendChild(card);
        });
    }

    createRoleCard(role) {
        const card = document.createElement('div');
        card.className = 'role-card';
        
        const permissionsList = role.permissions.map(p => `<li>${p}</li>`).join('');
        const systemBadge = role.is_system_role ? '<span class="system-badge">System Role</span>' : '';

        card.innerHTML = `
            <div class="role-header">
                <h3>${role.name} ${systemBadge}</h3>
                <span class="user-count">${role.user_count} users</span>
            </div>
            <p class="role-description">${role.description || 'No description provided'}</p>
            <div class="role-permissions">
                <h4>Permissions:</h4>
                <ul>${permissionsList}</ul>
            </div>
            <div class="role-actions">
                ${!role.is_system_role ? '<button class="btn-small btn-warning">Edit Role</button>' : ''}
                <button class="btn-small btn-secondary" onclick="roleManager.viewRoleUsers('${role.name}')">View Users</button>
            </div>
        `;

        return card;
    }

    openRoleModal(userId) {
        document.getElementById('modal-user').value = userId;
        
        // Populate role dropdown
        const roleSelect = document.getElementById('modal-role');
        roleSelect.innerHTML = this.roles.map(role => 
            `<option value="${role.name}">${role.name} - ${role.description}</option>`
        ).join('');

        document.getElementById('role-modal').style.display = 'block';
    }

    async assignRole() {
        const userId = document.getElementById('modal-user').value;
        const roleName = document.getElementById('modal-role').value;
        const expiresAt = document.getElementById('modal-expires').value || null;

        try {
            const response = await fetch('/admin/roles/api/grant', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    role_name: roleName,
                    expires_at: expiresAt
                })
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                this.closeModal();
                await this.init(); // Refresh data
            } else {
                const error = await response.json();
                alert('Error: ' + error.detail);
            }
        } catch (error) {
            alert('Error assigning role: ' + error.message);
        }
    }

    async revokeRole(userId, roleName) {
        if (!confirm(`Are you sure you want to revoke the "${roleName}" role from "${userId}"?`)) {
            return;
        }

        try {
            const response = await fetch('/admin/roles/api/revoke', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    role_name: roleName
                })
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                await this.init(); // Refresh data
            } else {
                const error = await response.json();
                alert('Error: ' + error.detail);
            }
        } catch (error) {
            alert('Error revoking role: ' + error.message);
        }
    }

    manageUserRoles(userId) {
        const userRole = this.users.find(ur => ur.user.id === userId);
        if (!userRole) return;

        const roleList = userRole.roles.map(role => {
            const expiryText = role.expires_at ? ` (expires ${new Date(role.expires_at).toLocaleDateString()})` : '';
            return `
                <div class="role-management-item">
                    <span>${role.name}${expiryText}</span>
                    <button class="btn-small btn-warning" onclick="roleManager.revokeRole('${userId}', '${role.name}')">
                        Revoke
                    </button>
                </div>
            `;
        }).join('');

        const modalContent = `
            <div class="modal-content">
                <h3>Manage Roles for ${userRole.user.display_name}</h3>
                <div class="user-roles-list">
                    ${roleList}
                </div>
                <button class="btn-secondary" onclick="this.closest('.modal').style.display='none'">Close</button>
            </div>
        `;

        // Create temporary modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = modalContent;
        document.body.appendChild(modal);
    }

    updateSummary() {
        document.getElementById('total-users').textContent = this.users.length;
        document.getElementById('total-roles').textContent = this.roles.length;
        
        const adminCount = this.users.filter(ur => 
            ur.roles.some(role => role.name === 'admin' && role.is_active)
        ).length;
        document.getElementById('admin-count').textContent = adminCount;
    }

    closeModal() {
        document.getElementById('role-modal').style.display = 'none';
        document.getElementById('role-form').reset();
    }

    filterUsers(searchTerm) {
        const rows = document.querySelectorAll('#user-roles-body tr');
        rows.forEach(row => {
            const userInfo = row.querySelector('.user-info strong').textContent.toLowerCase();
            const visible = userInfo.includes(searchTerm.toLowerCase());
            row.style.display = visible ? '' : 'none';
        });
    }

    async loadAuditLog() {
        try {
            const response = await fetch('/admin/roles/api/audit');
            const data = await response.json();
            
            const auditList = document.getElementById('audit-log-list');
            auditList.innerHTML = data.audit_entries.map(entry => `
                <div class="audit-entry">
                    <div class="audit-timestamp">${new Date(entry.timestamp).toLocaleString()}</div>
                    <div class="audit-action">${entry.action}</div>
                    <div class="audit-details">${entry.details}</div>
                    <div class="audit-performer">by ${entry.performed_by}</div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading audit log:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.roleManager = new RoleManager();
});

// Global functions for onclick handlers
function closeModal() {
    document.getElementById('role-modal').style.display = 'none';
}
```

### Phase 4: Integration & Security

#### Step 4.1: Integration with Existing Admin Routes
Update `app_helpers/routes/admin_routes.py`:

```python
# Add to existing imports
from .admin.role_management import router as role_mgmt_router

# Add to router includes
router.include_router(role_mgmt_router)
```

#### Step 4.2: Security Enhancements
```python
# Add to role management service
class RoleManagementService:
    def validate_role_assignment(self, user_id: str, role_name: str, assigned_by: str) -> List[str]:
        """Validate role assignment and return any warnings."""
        warnings = []
        
        # Check if assigning admin role
        if role_name == 'admin':
            warnings.append("Admin role grants full system access")
        
        # Check for role conflicts
        # Implementation depends on business rules
        
        return warnings
    
    def check_assignment_permissions(self, assigned_by: str, role_name: str) -> bool:
        """Check if user has permission to assign this role."""
        with Session(self.engine) as session:
            assigner = session.exec(select(User).where(User.display_name == assigned_by)).first()
            if not assigner:
                return False
            
            # Only admins can assign admin roles
            if role_name == 'admin':
                return assigner.has_role('admin', session)
            
            # Other role assignment rules
            return assigner.has_role('admin', session)
```

### Phase 5: Advanced Features

#### Step 5.1: Role Templates & Bulk Operations
```javascript
class BulkOperations {
    async bulkAssignRole(userIds, roleName, expiresAt = null) {
        const operations = userIds.map(userId => ({
            operation: 'grant',
            user_id: userId,
            role_name: roleName,
            expires_at: expiresAt
        }));

        const response = await fetch('/admin/roles/api/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ operations })
        });

        return await response.json();
    }
}
```

#### Step 5.2: Role Expiration Management
```python
# Add to service
def get_expiring_roles(self, days_ahead: int = 7) -> List[ExpiringRole]:
    """Get roles expiring within specified days."""
    cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
    
    with Session(self.engine) as session:
        stmt = (select(User, Role, UserRole)
               .join(UserRole, User.display_name == UserRole.user_id)
               .join(Role, UserRole.role_id == Role.id)
               .where(UserRole.expires_at.isnot(None))
               .where(UserRole.expires_at <= cutoff_date)
               .where(UserRole.expires_at > datetime.utcnow()))
        
        return list(session.exec(stmt))
```

## Implementation Timeline

### Week 1: Foundation
1. Create `RoleManagementService` class
2. Implement core role operations (grant, revoke, list)
3. Add comprehensive validation and error handling
4. Create basic API route structure

### Week 2: API Development
1. Implement all API endpoints
2. Add request/response models
3. Implement audit logging
4. Add comprehensive security checks

### Week 3: Frontend Development
1. Create admin roles template
2. Build JavaScript role manager
3. Implement user role matrix display
4. Add role assignment modals

### Week 4: Advanced Features
1. Add bulk operations
2. Implement role expiration management
3. Create audit log viewer
4. Add role creation interface

## Security Considerations

### Access Control
- **Admin Role Required**: Only admin users can access role management
- **Permission Checks**: Validate user permissions for each operation
- **Self-Assignment Prevention**: Prevent users from modifying their own admin status

### Audit & Compliance
- **Complete Audit Trail**: Log all role changes with timestamps and actors
- **Change History**: Track who made changes and when
- **Security Events**: Integrate with existing security logging

### Input Validation
- **Role Existence**: Validate roles exist before assignment
- **User Existence**: Validate users exist before role assignment
- **Expiration Dates**: Validate expiration dates are in the future
- **System Role Protection**: Prevent deletion of system roles

## Testing Strategy

### Unit Tests
```python
def test_role_management_service():
    # Test role assignment and revocation
    # Test validation logic
    # Test audit logging
    # Test permission checks

def test_role_api_endpoints():
    # Test admin authentication
    # Test role CRUD operations
    # Test bulk operations
    # Test error handling
```

### Integration Tests
```python
def test_role_management_workflow():
    # Test complete role assignment workflow
    # Test role expiration handling
    # Test audit log integration
    # Test UI interaction with API
```

## Success Metrics

### Usability
- **Time to Assign Role**: < 30 seconds for single assignment
- **Bulk Operation Speed**: Handle 100+ users in < 2 minutes
- **Error Rate**: < 2% failed operations

### Security
- **Audit Coverage**: 100% of role changes logged
- **Access Control**: 0 unauthorized role modifications
- **Permission Validation**: All operations properly validated

## Files to Create/Modify

### New Files
- `app_helpers/services/role_management_service.py` - Core service
- `app_helpers/routes/admin/role_management.py` - API routes
- `templates/admin_roles.html` - Main interface
- `static/js/admin-roles.js` - Frontend logic
- `static/css/admin-roles.css` - Styling

### Modifications
- `app_helpers/routes/admin_routes.py` - Include new routes
- `templates/admin.html` - Add link to role management
- `models.py` - Any additional role-related enhancements

This comprehensive role management interface will provide admins with powerful, secure tools to manage user permissions while maintaining full audit trails and safety measures.