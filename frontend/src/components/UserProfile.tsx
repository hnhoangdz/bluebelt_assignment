import React from 'react';
import { X } from 'lucide-react';
import './UserProfile.css';

interface UserProfileProps {
  user: any;
  onClose: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ user, onClose }) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>User Profile</h2>
          <button className="close-btn" onClick={onClose}>
            <X size={24} />
          </button>
        </div>
        <div className="profile-content">
          <div className="profile-field">
            <label>Username:</label>
            <span>{user.username}</span>
          </div>
          <div className="profile-field">
            <label>Email:</label>
            <span>{user.email}</span>
          </div>
          <div className="profile-field">
            <label>User ID:</label>
            <span>{user.id}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;