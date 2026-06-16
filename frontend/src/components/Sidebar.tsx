"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquare, FileText, BarChart3, LogOut, Cpu } from "lucide-react";
import { removeToken } from "@/services/api";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const menuItems = [
    { name: "Chat Engine", href: "/chat", icon: MessageSquare },
    { name: "Document Catalog", href: "/documents", icon: FileText },
    { name: "Observability", href: "/dashboard", icon: BarChart3 },
  ];

  const handleLogout = () => {
    removeToken();
    router.push("/login");
  };

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen shrink-0">
      {/* Brand Logo */}
      <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
        <div className="bg-blue-600 p-2 rounded-lg text-white">
          <Cpu className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-white leading-none">NexusAI</h1>
          <span className="text-xs text-slate-400">Enterprise Orchestrator</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-blue-600/20 text-blue-400 border-l-4 border-blue-500 pl-3"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer / User Profile */}
      <div className="p-4 border-t border-slate-800">
        <button
          onClick={handleLogout}
          className="flex items-center space-x-3 w-full px-4 py-3 text-sm font-medium text-slate-400 hover:bg-red-950/20 hover:text-red-400 rounded-lg transition-colors duration-200"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
