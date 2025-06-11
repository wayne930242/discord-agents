import { type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { authAPI } from "@/lib/api";

interface LayoutProps {
  children: ReactNode;
  title: string;
  subtitle?: string;
  showBackButton?: boolean;
  backTo?: string;
  extraActions?: ReactNode;
}

export function Layout({
  children,
  title,
  subtitle,
  showBackButton = false,
  backTo = "/dashboard",
  extraActions,
}: LayoutProps) {
  const navigate = useNavigate();

  const handleLogout = () => {
    authAPI.logout();
    navigate("/login");
  };

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-2">{subtitle}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            登出
          </Button>
          {showBackButton && (
            <Button variant="outline" asChild>
              <Link to={backTo}>返回</Link>
            </Button>
          )}
          {extraActions}
        </div>
      </div>
      {children}
    </div>
  );
}
