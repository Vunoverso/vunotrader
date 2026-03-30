import { ReactNode } from "react";

type SectionShellProps = {
  id?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function SectionShell({
  id,
  eyebrow,
  title,
  description,
  children,
  className = "",
}: SectionShellProps) {
  return (
    <section id={id} className={`relative py-20 sm:py-24 ${className}`.trim()}>
      <div className="mx-auto w-full max-w-6xl px-6 lg:px-8">
        <div className="max-w-2xl">
          {eyebrow ? (
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">
              {eyebrow}
            </p>
          ) : null}
          <h2 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">{title}</h2>
          {description ? (
            <p className="mt-4 text-lg leading-8 text-slate-600">{description}</p>
          ) : null}
        </div>
        <div className="mt-12">{children}</div>
      </div>
    </section>
  );
}