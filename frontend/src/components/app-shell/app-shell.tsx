'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { useMemo } from 'react';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { HelpCircle, Menu, Settings } from 'lucide-react';
import { FlowHeader } from '@/features/flow/components/flow-header';
import { useState } from 'react';

interface AppShellProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard' },
  // { label: 'Search', href: '/search' },  // Hidden - workflow starts from NCT Search
  { label: 'NCT Search', href: '/ct-search' },
  { label: 'Schema', href: '/schema' },
  { label: 'Cohort', href: '/cohort' },
  { label: 'Analysis', href: '/analysis' },
  { label: 'Report', href: '/report' },
  { label: 'Settings', href: '/settings' },
  { label: 'Help', href: '/help' },
];

const FLOW_ROUTES = new Set(['/search', '/ct-search', '/schema', '/cohort', '/analysis', '/report']);

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const activeHref = useMemo(() => {
    if (!pathname) return '/dashboard';
    const match = NAV_ITEMS.find((item) => pathname === item.href);
    if (match) return match.href;
    const partialMatch = NAV_ITEMS.find((item) =>
      pathname.startsWith(item.href) && item.href !== '/dashboard',
    );
    return partialMatch?.href ?? '/dashboard';
  }, [pathname]);

  const showFlowHeader = useMemo(
    () => Boolean(pathname && [...FLOW_ROUTES].some((route) => pathname.startsWith(route))),
    [pathname],
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex min-h-screen flex-col bg-background">
        <div className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/75">
          <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <Link href="/dashboard" className="flex items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/telos-text-logo.png"
                  alt="TELOS"
                  className="h-7 w-auto object-contain"
                />
              </Link>
            </div>
            <nav className="hidden flex-1 items-center justify-center gap-1 text-sm font-medium md:flex">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  active={activeHref === item.href}
                />
              ))}
            </nav>
            <div className="flex items-center gap-1">
              <div className="md:hidden">
                <Sheet open={open} onOpenChange={setOpen}>
                  <SheetTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Open navigation menu"
                    >
                      <Menu className="h-5 w-5" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="w-[280px]">
                    <SheetHeader className="items-start text-left">
                      <SheetTitle className="text-lg font-semibold text-foreground">
                        Navigation
                      </SheetTitle>
                    </SheetHeader>
                    <div className="mt-4 flex flex-col gap-2">
                      {NAV_ITEMS.map((item) => (
                        <Button
                          key={item.href}
                          variant={activeHref === item.href ? 'default' : 'ghost'}
                          className="justify-start"
                          asChild
                          onClick={() => setOpen(false)}
                        >
                          <Link href={item.href}>{item.label}</Link>
                        </Button>
                      ))}
                    </div>
                  </SheetContent>
                </Sheet>
              </div>
              <div className="hidden md:flex md:items-center md:gap-1">
                <IconButton label="Help Center" href="/help">
                  <HelpCircle className="h-5 w-5" />
                </IconButton>
                <IconButton label="Settings" href="/settings">
                  <Settings className="h-5 w-5" />
                </IconButton>
              </div>
              <div className="ml-3 flex items-center gap-2 rounded-md border border-border/60 bg-muted/30 px-3 py-1.5">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-sm font-medium text-foreground">이국종</span>
              </div>
            </div>
          </div>
        </div>
        {showFlowHeader ? <FlowHeader /> : null}
        <main className="flex-1">
          <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>
        </main>
      </div>
    </TooltipProvider>
  );
}

interface NavLinkProps {
  href: string;
  label: string;
  active: boolean;
}

function NavLink({ href, label, active }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={cn(
        'rounded-md px-3 py-1.5 transition-colors',
        active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
      )}
    >
      {label}
    </Link>
  );
}

interface IconButtonProps {
  label: string;
  href: string;
  children: ReactNode;
}

function IconButton({ label, href, children }: IconButtonProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 text-muted-foreground hover:text-foreground"
          asChild
        >
          <Link href={href} aria-label={label}>
            {children}
          </Link>
        </Button>
      </TooltipTrigger>
      <TooltipContent sideOffset={8}>{label}</TooltipContent>
    </Tooltip>
  );
}
