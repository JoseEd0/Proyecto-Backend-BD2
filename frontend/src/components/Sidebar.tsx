import { NavLink } from "react-router-dom";
import {
  Database,
  Image,
  FileText,
  Table,
  Settings,
  Music,
} from "lucide-react";
import "./Sidebar.css";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Database size={32} />
        <h1>BD2 Manager</h1>
        <p>Multi-Structure Database</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/sql"
          className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
        >
          <Database size={20} />
          <span>SQL Console</span>
        </NavLink>

        <NavLink
          to="/sift"
          className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
        >
          <Image size={20} />
          <span>SIFT Images</span>
        </NavLink>

        <NavLink
          to="/bow"
          className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
        >
          <FileText size={20} />
          <span>BoW Documents</span>
        </NavLink>

        <NavLink
          to="/audio"
          className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
        >
          <Music size={20} />
          <span>Audio MFCC</span>
        </NavLink>

        <NavLink
          to="/tables"
          className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
        >
          <Table size={20} />
          <span>Tables View</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-info">
          <Settings size={16} />
          <span>v2.0.0</span>
        </div>
        <p className="sidebar-copyright">UTEC © 2025</p>
      </div>
    </aside>
  );
}
