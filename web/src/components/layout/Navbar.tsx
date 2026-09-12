import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ShieldCheck, BarChart3, Sliders, BookOpen, MapPin, FileText } from "lucide-react";

export const Navbar: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "風險排行", icon: BarChart3 },
    { path: "/map", label: "風險地圖", icon: MapPin },
    { path: "/report", label: "綜整報告", icon: FileText },
    { path: "/sandbox", label: "權重沙盒", icon: Sliders },
    { path: "/method", label: "模型方法論", icon: BookOpen },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 text-white rounded-lg shadow-sm">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900 block leading-tight">
                小小守護員 Smart Watchdog
              </span>
              <span className="text-xs text-slate-500 block">新北市幼兒園風險預警系統</span>
            </div>
          </Link>

          <nav className="flex space-x-1 sm:space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
};
