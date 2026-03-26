import { NavLink, Outlet } from 'react-router-dom';
import { NAV_ITEMS } from '../styles/theme';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top navigation bar */}
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-[#2171B5]">LinkD Agent</h1>
              <span className="text-xs text-gray-400 hidden sm:inline">Multi-Evidence Supported Drug Discovery Platform</span>
            </div>
            <div className="flex gap-1">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? 'bg-[#2171B5] text-white'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
}
