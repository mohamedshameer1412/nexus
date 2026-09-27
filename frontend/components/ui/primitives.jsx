"use client";
// The Nexus component kit: Radix primitives styled with Tailwind (shadcn-style), one file so every screen imports from one place.
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import * as LabelPrimitive from "@radix-ui/react-label";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";
import * as DropdownPrimitive from "@radix-ui/react-dropdown-menu";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import * as SelectPrimitive from "@radix-ui/react-select";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as PopoverPrimitive from "@radix-ui/react-popover";
import * as SliderPrimitive from "@radix-ui/react-slider";
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import { cva } from "class-variance-authority";
import { Check, ChevronDown, Circle, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ------------------------------------------------------------------------------------------------ button

export const buttonVariants = cva(
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold transition-[background,color,box-shadow,transform] active:translate-y-px disabled:pointer-events-none disabled:opacity-55 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-brand-deep text-white shadow-[0_1px_0_rgb(255_255_255/.15)_inset,0_4px_12px_-4px_rgb(3_105_168/.55)] hover:bg-[#02588D]",
        brand: "bg-brand text-white hover:bg-brand-deep",
        secondary: "border border-border bg-surface text-foreground shadow-sm hover:border-brand/40 hover:bg-brand-wash",
        ghost: "text-foreground hover:bg-brand-soft/60",
        subtle: "bg-brand-soft/70 text-brand-deep hover:bg-brand-soft",
        danger: "bg-weak text-white hover:bg-[#A82C23]",
        "danger-outline": "border border-weak/30 bg-surface text-weak hover:bg-weak-bg",
        link: "h-auto p-0 text-link underline-offset-4 hover:underline",
      },
      size: { default: "h-10 px-4", sm: "h-8 px-3 text-[13px]", lg: "h-11 px-5 text-[15px]", icon: "h-10 w-10 p-0", "icon-sm": "h-8 w-8 p-0" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

/**
 * @type {React.ForwardRefExoticComponent<any>}
 */
export const Button = React.forwardRef(function Button({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={asChild ? undefined : disabled || loading} aria-busy={loading || undefined} {...props}>
      {asChild ? children : (<>{loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}{children}</>)}
    </Comp>
  );
});

// ------------------------------------------------------------------------------------------------ form fields

const field = "w-full rounded-md border border-border bg-surface px-3 text-[15px] text-foreground shadow-[inset_0_1px_2px_rgb(11_34_57/.04)] placeholder:text-muted/80 transition-colors hover:border-brand/40 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:opacity-60 aria-[invalid=true]:border-weak aria-[invalid=true]:ring-weak/15";

export const Input = React.forwardRef(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(field, "h-10 py-2", className)} {...props} />;
});

export const Textarea = React.forwardRef(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(field, "min-h-24 py-2.5 leading-relaxed", className)} {...props} />;
});

export const Label = React.forwardRef(function Label({ className, ...props }, ref) {
  return <LabelPrimitive.Root ref={ref} className={cn("mb-1.5 block text-[13px] font-semibold text-foreground", className)} {...props} />;
});

export function Field({ label, htmlFor, hint, error, children, className }) {
  return (
    <div className={className}>
      {label && <Label htmlFor={htmlFor}>{label}</Label>}
      {children}
      {error ? <p className="mt-1 text-[13px] font-medium text-weak" role="alert">{error}</p> : hint ? <p className="mt-1 text-[13px] text-muted">{hint}</p> : null}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ surfaces

export function Card({ className = "", interactive = false, ...props }) {
  return <div className={cn("rounded-xl border border-border/80 bg-surface shadow-card", interactive && "transition-shadow hover:shadow-lift", className)} {...props} />;
}
export function CardHeader({ title, description, action, className, icon: Icon }) {
  return (
    <div className={cn("flex items-start justify-between gap-3 px-5 pt-4", className)}>
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 text-[15px] font-semibold text-foreground">{Icon && <Icon className="h-4 w-4 text-brand" aria-hidden="true" />}{title}</h2>
        {description && <p className="mt-0.5 text-[13px] text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
export function CardBody({ className, ...props }) {
  return <div className={cn("px-5 pb-5 pt-3", className)} {...props} />;
}

const tones = {
  neutral: "bg-brand-soft/70 text-brand-ink",
  brand: "bg-brand text-white",
  outline: "border border-border bg-surface text-muted",
  success: "bg-strong-bg text-strong",
  strong: "bg-strong-bg text-strong",
  warning: "bg-mid-bg text-mid",
  mid: "bg-mid-bg text-mid",
  danger: "bg-weak-bg text-weak",
  weak: "bg-weak-bg text-weak",
  muted: "bg-surface-2 text-muted border border-border",
};
export function Badge({ className = "", tone = "neutral", dot = false, ...props }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[12px] font-semibold leading-5", tones[tone], className)} {...props}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {props.children}
    </span>
  );
}

export function Alert({ tone = "info", className, icon: Icon, title, children, ...props }) {
  const t = { warning: "border-mid/25 bg-mid-bg text-[#7A4A00]", danger: "border-weak/25 bg-weak-bg text-[#8F2219]", success: "border-strong/25 bg-strong-bg text-[#0A5F42]", info: "border-brand/20 bg-brand-wash text-brand-ink" };
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cn("flex gap-3 rounded-lg border px-3.5 py-2.5 text-sm", t[tone], className)} {...props}>
      {Icon && <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
      <div className="min-w-0">{title && <p className="font-semibold">{title}</p>}<div>{children}</div></div>
    </div>
  );
}

export function Skeleton({ className, ...props }) {
  return <div aria-hidden="true" className={cn("skeleton animate-shimmer rounded-md", className)} {...props} />;
}

export function Progress({ value = 0, className, indicatorClassName, ...props }) {
  return (
    <ProgressPrimitive.Root value={value} className={cn("relative h-2 w-full overflow-hidden rounded-full bg-brand-soft/70", className)} {...props}>
      <ProgressPrimitive.Indicator className={cn("h-full rounded-full bg-brand transition-[width] duration-500", indicatorClassName)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </ProgressPrimitive.Root>
  );
}

export function Separator({ className }) {
  return <div role="separator" className={cn("h-px w-full bg-border", className)} />;
}

export function Kbd({ children, className }) {
  return <kbd className={cn("rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[11px] font-semibold text-muted", className)}>{children}</kbd>;
}

// ------------------------------------------------------------------------------------------------ dialog

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

/** A centred dialog on tablets and desktops, a bottom sheet on phones. */
export function DialogContent({ className, children, title, description, wide, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-brand-ink/45 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content
        className={cn(
          "fixed z-50 w-full border border-border bg-surface p-6 shadow-pop focus:outline-none",
          "bottom-0 left-0 max-h-[92dvh] overflow-y-auto rounded-t-2xl pb-[max(1.5rem,env(safe-area-inset-bottom))]",
          "sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl",
          "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom-4 sm:data-[state=open]:zoom-in-95 sm:data-[state=open]:slide-in-from-bottom-0",
          wide ? "sm:max-w-2xl" : "sm:max-w-md",
          className,
        )}
        {...props}
      >
        <DialogPrimitive.Title className="pr-10 font-display text-lg font-semibold">{title}</DialogPrimitive.Title>
        {description ? <DialogPrimitive.Description className="mt-1 text-sm text-muted">{description}</DialogPrimitive.Description>
          : <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>}
        <div className="mt-5">{children}</div>
        <DialogPrimitive.Close className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-md text-muted hover:bg-brand-wash hover:text-foreground" aria-label="Close">
          <X className="h-4 w-4" aria-hidden="true" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/** A confirmation for a destructive action. */
export function ConfirmDialog({ trigger, title, description, confirm = "Delete", tone = "danger", onConfirm, loading, open, onOpenChange }) {
  return (
    <AlertDialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <AlertDialogPrimitive.Trigger asChild>{trigger}</AlertDialogPrimitive.Trigger>}
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 z-40 bg-brand-ink/45 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <AlertDialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-surface p-6 shadow-pop data-[state=open]:animate-in data-[state=open]:zoom-in-95 data-[state=open]:fade-in-0">
          <AlertDialogPrimitive.Title className="font-display text-lg font-semibold">{title}</AlertDialogPrimitive.Title>
          <AlertDialogPrimitive.Description className="mt-2 text-sm text-muted">{description}</AlertDialogPrimitive.Description>
          <div className="mt-6 flex justify-end gap-2">
            <AlertDialogPrimitive.Cancel asChild><Button variant="secondary">Cancel</Button></AlertDialogPrimitive.Cancel>
            <Button variant={tone === "danger" ? "danger" : "default"} loading={loading} onClick={onConfirm}>{confirm}</Button>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}

/** A panel sliding in from the right (details, filters). */
export function Sheet({ open, onOpenChange, title, description, children, className }) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-brand-ink/40 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className={cn("fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-border bg-surface shadow-pop focus:outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-right", className)}>
          <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
            <div>
              <DialogPrimitive.Title className="font-display text-lg font-semibold">{title}</DialogPrimitive.Title>
              <DialogPrimitive.Description className={description ? "mt-0.5 text-sm text-muted" : "sr-only"}>{description || title}</DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted hover:bg-brand-wash" aria-label="Close"><X className="h-4 w-4" /></DialogPrimitive.Close>
          </div>
          <div className="nx-scroll-light flex-1 overflow-y-auto px-5 py-4">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

// ------------------------------------------------------------------------------------------------ menus, popovers, tooltips

export const DropdownMenu = DropdownPrimitive.Root;
export const DropdownMenuTrigger = DropdownPrimitive.Trigger;
export function DropdownMenuContent({ className = "", align = "end", ...props }) {
  return (
    <DropdownPrimitive.Portal>
      <DropdownPrimitive.Content align={align} sideOffset={6} className={cn("z-50 min-w-48 rounded-lg border border-border bg-surface p-1 shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95", className)} {...props} />
    </DropdownPrimitive.Portal>
  );
}
export function DropdownMenuItem({ className = "", ...props }) {
  return <DropdownPrimitive.Item className={cn("flex h-9 cursor-pointer select-none items-center gap-2 rounded-md px-2.5 text-sm outline-none data-[highlighted]:bg-brand-wash data-[highlighted]:text-brand-deep [&_svg]:h-4 [&_svg]:w-4", className)} {...props} />;
}
export function DropdownMenuLabel({ className = "", ...props }) {
  return <DropdownPrimitive.Label className={cn("px-2.5 py-1.5 text-[12px] font-semibold text-muted", className)} {...props} />;
}
export function DropdownMenuSeparator() {
  return <DropdownPrimitive.Separator className="my-1 h-px bg-border" />;
}

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export function PopoverContent({ className, align = "start", ...props }) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content align={align} sideOffset={6} className={cn("z-50 w-72 rounded-lg border border-border bg-surface p-3 shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95", className)} {...props} />
    </PopoverPrimitive.Portal>
  );
}

export const TooltipProvider = TooltipPrimitive.Provider;
export function Tooltip({ content, children, side = "top" }) {
  if (!content) return children;
  return (
    <TooltipPrimitive.Root delayDuration={250}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content side={side} sideOffset={6} className="z-50 max-w-xs rounded-md bg-brand-ink px-2.5 py-1.5 text-[12.5px] leading-snug text-white shadow-pop data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0">
          {content}
          <TooltipPrimitive.Arrow className="fill-brand-ink" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

// ------------------------------------------------------------------------------------------------ tabs, segmented control

export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }) {
  return <TabsPrimitive.List className={cn("inline-flex items-center gap-1 rounded-lg bg-brand-soft/60 p-1", className)} {...props} />;
}
export function TabsTrigger({ className, ...props }) {
  return <TabsPrimitive.Trigger className={cn("inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-[13px] font-semibold text-muted transition-colors hover:text-foreground data-[state=active]:bg-surface data-[state=active]:text-brand-deep data-[state=active]:shadow-sm [&_svg]:h-4 [&_svg]:w-4", className)} {...props} />;
}
export const TabsContent = TabsPrimitive.Content;

export function Segmented({ value, onValueChange, options, className, label }) {
  return (
    <ToggleGroupPrimitive.Root type="single" value={value} onValueChange={(v) => v && onValueChange(v)} aria-label={label} className={cn("inline-flex items-center gap-1 rounded-lg bg-brand-soft/60 p-1", className)}>
      {options.map((o) => (
        <ToggleGroupPrimitive.Item key={o.value} value={o.value} className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-[13px] font-semibold text-muted transition-colors hover:text-foreground data-[state=on]:bg-surface data-[state=on]:text-brand-deep data-[state=on]:shadow-sm">
          {o.icon && <o.icon className="h-4 w-4" aria-hidden="true" />}{o.label}
        </ToggleGroupPrimitive.Item>
      ))}
    </ToggleGroupPrimitive.Root>
  );
}

// ------------------------------------------------------------------------------------------------ select, checkbox, radio, switch, slider

export const Select = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;
export const SelectTrigger = React.forwardRef(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger ref={ref} className={cn(field, "flex h-10 items-center justify-between gap-2 py-2 text-left data-[placeholder]:text-muted", className)} {...props}>
    <span className="truncate">{children}</span>
    <SelectPrimitive.Icon asChild><ChevronDown className="h-4 w-4 shrink-0 text-muted" /></SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = "SelectTrigger";
export const SelectContent = React.forwardRef(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content ref={ref} position={position} sideOffset={4}
      className={cn("relative z-50 max-h-80 min-w-[8rem] overflow-hidden rounded-lg border border-border bg-surface shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0", className)} {...props}>
      <SelectPrimitive.Viewport className={cn("p-1", position === "popper" && "w-full min-w-[var(--radix-select-trigger-width)]")}>{children}</SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = "SelectContent";
export const SelectItem = React.forwardRef(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item ref={ref} className={cn("relative flex h-9 w-full cursor-pointer select-none items-center rounded-md pl-8 pr-2 text-sm outline-none data-[highlighted]:bg-brand-wash data-[highlighted]:text-brand-deep data-[disabled]:opacity-50", className)} {...props}>
    <span className="absolute left-2 flex h-4 w-4 items-center justify-center"><SelectPrimitive.ItemIndicator><Check className="h-4 w-4" /></SelectPrimitive.ItemIndicator></span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = "SelectItem";

export const Checkbox = React.forwardRef(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root ref={ref} className={cn("peer h-[18px] w-[18px] shrink-0 rounded-[5px] border border-brand-deep/60 bg-surface transition-colors data-[state=checked]:border-brand-deep data-[state=checked]:bg-brand-deep data-[state=checked]:text-white disabled:opacity-50", className)} {...props}>
    <CheckboxPrimitive.Indicator className="flex items-center justify-center"><Check className="h-3.5 w-3.5" strokeWidth={3} /></CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));
Checkbox.displayName = "Checkbox";

export const RadioGroup = React.forwardRef(({ className, ...props }, ref) => <RadioGroupPrimitive.Root ref={ref} className={cn("grid gap-2", className)} {...props} />);
RadioGroup.displayName = "RadioGroup";
export const RadioGroupItem = React.forwardRef(({ className, ...props }, ref) => (
  <RadioGroupPrimitive.Item ref={ref} className={cn("aspect-square h-[18px] w-[18px] shrink-0 rounded-full border border-brand-deep/60 bg-surface text-brand-deep data-[state=checked]:border-brand-deep disabled:opacity-50", className)} {...props}>
    <RadioGroupPrimitive.Indicator className="flex items-center justify-center"><Circle className="h-2.5 w-2.5 fill-current" /></RadioGroupPrimitive.Indicator>
  </RadioGroupPrimitive.Item>
));
RadioGroupItem.displayName = "RadioGroupItem";

export const Switch = React.forwardRef(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root ref={ref} className={cn("inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent bg-border transition-colors data-[state=checked]:bg-brand-deep disabled:opacity-50", className)} {...props}>
    <SwitchPrimitive.Thumb className="pointer-events-none block h-5 w-5 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0" />
  </SwitchPrimitive.Root>
));
Switch.displayName = "Switch";

export const Slider = React.forwardRef(({ className, label, ...props }, ref) => (
  <SliderPrimitive.Root ref={ref} className={cn("relative flex h-5 w-full touch-none select-none items-center", className)} {...props}>
    <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-brand-soft"><SliderPrimitive.Range className="absolute h-full bg-brand" /></SliderPrimitive.Track>
    <SliderPrimitive.Thumb aria-label={label} className="block h-5 w-5 rounded-full border-2 border-brand bg-white shadow transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand/25" />
  </SliderPrimitive.Root>
));
Slider.displayName = "Slider";
