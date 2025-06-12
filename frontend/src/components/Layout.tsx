import { type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

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
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2 mb-2">
            {showBackButton && (
              <Button variant="ghost" size="icon" asChild>
                <Link to={backTo}>
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
            )}
            <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
          </div>
          {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
        </div>
        {extraActions && (
          <div className="flex gap-2">
            {extraActions}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}
