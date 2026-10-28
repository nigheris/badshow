import * as React from "react";
import * as RadixTabs from "@radix-ui/react-tabs";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";
import { cn } from "../lib/utils";

export const buttonVariants = cva("ui-button", {
  variants: {
    variant: {
      default: "ui-button-default",
      outline: "ui-button-outline",
      ghost: "ui-button-ghost",
    },
    size: {
      default: "ui-button-md",
      sm: "ui-button-sm",
      icon: "ui-button-icon",
    },
  },
  defaultVariants: {
    variant: "default",
    size: "default",
  },
});

export const Button = React.forwardRef(function Button(
  { className, variant, size, asChild = false, ...props },
  ref,
) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
});

export function Card({ className, ...props }) {
  return <section className={cn("ui-card", className)} {...props} />;
}

export function CardHeader({ className, ...props }) {
  return <div className={cn("ui-card-header", className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return <h2 className={cn("ui-card-title", className)} {...props} />;
}

export function CardDescription({ className, ...props }) {
  return <p className={cn("ui-card-description", className)} {...props} />;
}

export function CardContent({ className, ...props }) {
  return <div className={cn("ui-card-content", className)} {...props} />;
}

export const Badge = React.forwardRef(function Badge(
  { className, variant = "muted", ...props },
  ref,
) {
  return (
    <span
      ref={ref}
      className={cn("ui-badge", `ui-badge-${variant}`, className)}
      {...props}
    />
  );
});

export const Tabs = {
  Root: RadixTabs.Root,
  List: (props) => <RadixTabs.List {...props} className={cn("ui-tabs-list", props.className)} />,
  Trigger: (props) => <RadixTabs.Trigger {...props} className={cn("ui-tabs-trigger", props.className)} />,
  Content: (props) => <RadixTabs.Content {...props} className={cn("ui-tabs-content", props.className)} />,
};

export function Table({ className, ...props }) {
  return (
    <div className="ui-table-wrap">
      <table className={cn("ui-table", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }) {
  return <thead className={cn("ui-table-header", className)} {...props} />;
}

export function TableBody({ className, ...props }) {
  return <tbody className={cn("ui-table-body", className)} {...props} />;
}

export function TableRow({ className, ...props }) {
  return <tr className={cn("ui-table-row", className)} {...props} />;
}

export function TableHead({ className, ...props }) {
  return <th className={cn("ui-table-head", className)} {...props} />;
}

export function TableCell({ className, ...props }) {
  return <td className={cn("ui-table-cell", className)} {...props} />;
}