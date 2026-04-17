"use client";

import { cn } from "@/lib/utils";

export function PageContainer({ 
  children, 
  className,
  fullBleed = false 
}: { 
  children: React.ReactNode; 
  className?: string;
  fullBleed?: boolean;
}) {
  if (fullBleed) {
    return (
      <div className={cn("h-screen w-full overflow-hidden", className)}>
        {children}
      </div>
    );
  }

  return (
    <div className={cn("mx-auto max-w-7xl px-4 pb-16 pt-20 md:px-10 md:pt-10 transition-all duration-500", className)}>
      {children}
    </div>
  );
}
