"""
Authentication and Authorization Service
RBAC implementation for NotarFlow
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import hashlib
import secrets

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from config.settings import settings, UserRole
from db.models import User, Organization, Session as UserSession, AuditLog

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = settings.SESSION_EXPIRY_HOURS


class AuthService:
    """Authentication and authorization service."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # PASSWORD MANAGEMENT
    # =========================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # =========================================================================
    # TOKEN MANAGEMENT
    # =========================================================================

    def create_access_token(self, user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid4())  # JWT ID for revocation
        }

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    def create_session(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create a new user session and return the token."""
        token = self.create_access_token(user_id)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            ip_address=ip_address,
            user_agent=user_agent,
            is_valid=True
        )

        self.db.add(session)
        self.db.commit()

        return token

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a user session."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        session = self.db.query(UserSession).filter(
            UserSession.token_hash == token_hash
        ).first()

        if session:
            session.is_valid = False
            self.db.commit()
            return True

        return False

    def validate_session(self, token: str) -> Optional[User]:
        """Validate a session token and return the user if valid."""
        payload = self.decode_token(token)
        if not payload:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        session = self.db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
            UserSession.is_valid == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()

        if not session:
            return None

        user = self.db.query(User).filter(
            User.id == UUID(payload["sub"]),
            User.is_active == True,
            User.is_deleted == False
        ).first()

        return user

    # =========================================================================
    # USER AUTHENTICATION
    # =========================================================================

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.db.query(User).filter(
            User.email == email.lower(),
            User.is_active == True,
            User.is_deleted == False
        ).first()

        if not user:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Login user and create session."""
        user = self.authenticate_user(email, password)

        if not user:
            self._log_audit(
                action="login_failed",
                resource_type="user",
                description=f"Failed login attempt for email: {email}",
                ip_address=ip_address
            )
            return None

        token = self.create_session(user.id, ip_address, user_agent)

        self._log_audit(
            action="login",
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            description=f"User logged in: {user.email}",
            ip_address=ip_address
        )

        return {
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "organization_id": str(user.organization_id) if user.organization_id else None
            }
        }

    def logout(self, token: str) -> bool:
        """Logout user and invalidate session."""
        user = self.validate_session(token)

        if user:
            self._log_audit(
                action="logout",
                resource_type="user",
                resource_id=user.id,
                user_id=user.id,
                description=f"User logged out: {user.email}"
            )

        return self.invalidate_session(token)

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str,
        organization_id: Optional[UUID] = None,
        title: Optional[str] = None,
        phone: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = self.db.query(User).filter(User.email == email.lower()).first()
        if existing:
            raise ValueError(f"User with email {email} already exists")

        user = User(
            email=email.lower(),
            password_hash=self.hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            organization_id=organization_id,
            title=title,
            phone=phone,
            is_active=True,
            created_by=created_by
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        self._log_audit(
            action="create",
            resource_type="user",
            resource_id=user.id,
            user_id=created_by,
            description=f"User created: {user.email} with role {role}"
        )

        return user

    def update_user(
        self,
        user_id: UUID,
        updated_by: UUID,
        **kwargs
    ) -> Optional[User]:
        """Update user details."""
        user = self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()

        if not user:
            return None

        old_values = {}
        new_values = {}

        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['id', 'password_hash', 'created_at']:
                old_values[key] = getattr(user, key)
                if key == 'password':
                    setattr(user, 'password_hash', self.hash_password(value))
                    new_values['password'] = '***'
                else:
                    setattr(user, key, value)
                    new_values[key] = value

        user.updated_by = updated_by
        self.db.commit()
        self.db.refresh(user)

        self._log_audit(
            action="update",
            resource_type="user",
            resource_id=user.id,
            user_id=updated_by,
            description=f"User updated: {user.email}",
            old_values=old_values,
            new_values=new_values
        )

        return user

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(
            User.email == email.lower(),
            User.is_deleted == False
        ).first()

    def get_users_by_organization(
        self,
        organization_id: UUID,
        role: Optional[str] = None
    ) -> List[User]:
        """Get all users for an organization."""
        query = self.db.query(User).filter(
            User.organization_id == organization_id,
            User.is_deleted == False
        )

        if role:
            query = query.filter(User.role == role)

        return query.all()

    # =========================================================================
    # AUTHORIZATION / RBAC
    # =========================================================================

    def check_permission(
        self,
        user: User,
        resource_type: str,
        action: str,
        resource_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if user has permission to perform action on resource.

        RBAC Matrix:
        - admin: Full access to all resources in organization
        - rechtsanwalt: Full access to cases, documents, can manage external users
        - glaeubigerin: View own cases, report payments, approve enforcement
        - schuldner: View own case, request payment plans, upload documents
        """
        role = user.role

        # Admin has full access
        if role == UserRole.ADMIN:
            return True

        # Define permission matrix
        permissions = {
            UserRole.RECHTSANWALT: {
                "case": ["create", "read", "update", "delete", "assign"],
                "document": ["create", "read", "update", "delete", "upload"],
                "booking": ["create", "read", "update", "delete", "approve"],
                "message": ["create", "read", "send"],
                "payment_plan": ["create", "read", "update", "approve", "reject"],
                "dunning": ["create", "read", "update", "send"],
                "enforcement": ["create", "read", "update", "execute"],
                "user": ["read", "create_external"],
                "inbox": ["read", "assign", "process"],
            },
            UserRole.GLAEUBIGERIN: {
                "case": ["read_own"],
                "document": ["read_own", "upload_own"],
                "booking": ["read_own", "report_payment"],
                "message": ["read_own", "send_own"],
                "payment_plan": ["read_own"],
                "dunning": ["read_own"],
                "enforcement": ["read_own", "approve", "reject"],
                "user": [],
                "inbox": [],
            },
            UserRole.SCHULDNER: {
                "case": ["read_own"],
                "document": ["read_visible", "upload_own"],
                "booking": ["read_own"],
                "message": ["read_own", "send_own"],
                "payment_plan": ["read_own", "request"],
                "dunning": ["read_own"],
                "enforcement": ["read_own"],
                "user": [],
                "inbox": [],
            },
        }

        role_permissions = permissions.get(role, {})
        resource_permissions = role_permissions.get(resource_type, [])

        return action in resource_permissions

    def can_access_case(self, user: User, case_id: UUID) -> bool:
        """Check if user can access a specific case."""
        from db.models import Case

        if user.role == UserRole.ADMIN:
            return True

        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return False

        if user.role == UserRole.RECHTSANWALT:
            # RA can access cases in their organization
            return case.organization_id == user.organization_id

        if user.role == UserRole.GLAEUBIGERIN:
            # Creditor can only access their own cases
            return case.creditor_user_id == user.id

        if user.role == UserRole.SCHULDNER:
            # Debtor can only access their own cases
            return case.debtor_user_id == user.id

        return False

    def can_access_document(self, user: User, document) -> bool:
        """Check if user can access a specific document."""
        if user.role in [UserRole.ADMIN, UserRole.RECHTSANWALT]:
            if document.organization_id:
                return document.organization_id == user.organization_id
            if document.case_id:
                return self.can_access_case(user, document.case_id)
            return True

        if user.role == UserRole.GLAEUBIGERIN:
            if not document.visible_to_creditor:
                return False
            if document.case_id:
                return self.can_access_case(user, document.case_id)
            return False

        if user.role == UserRole.SCHULDNER:
            if not document.visible_to_debtor:
                return False
            if document.case_id:
                return self.can_access_case(user, document.case_id)
            return False

        return False

    # =========================================================================
    # ORGANIZATION MANAGEMENT
    # =========================================================================

    def create_organization(
        self,
        name: str,
        slug: str,
        created_by: Optional[UUID] = None,
        **kwargs
    ) -> Organization:
        """Create a new organization."""
        org = Organization(
            name=name,
            slug=slug.lower(),
            **kwargs
        )

        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)

        self._log_audit(
            action="create",
            resource_type="organization",
            resource_id=org.id,
            user_id=created_by,
            organization_id=org.id,
            description=f"Organization created: {name}"
        )

        return org

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    def _log_audit(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        case_id: Optional[UUID] = None
    ):
        """Log an audit entry."""
        user = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()

        log = AuditLog(
            user_id=user_id,
            user_email=user.email if user else None,
            user_role=user.role if user else None,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            case_id=case_id
        )

        self.db.add(log)
        # Don't commit here - let the calling function handle the transaction

    def get_audit_logs(
        self,
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        case_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with optional filters."""
        query = self.db.query(AuditLog)

        if organization_id:
            query = query.filter(AuditLog.organization_id == organization_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if case_id:
            query = query.filter(AuditLog.case_id == case_id)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()


# Utility function for password generation
def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    return secrets.token_urlsafe(length)
