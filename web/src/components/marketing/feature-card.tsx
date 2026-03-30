"use client";

import { motion } from "framer-motion";

type FeatureCardProps = {
  title: string;
  description: string;
  icon: React.ReactNode;
  gradient?: string;
};

export function FeatureCard({ title, description, icon, gradient = "from-cyan-500 to-sky-700" }: FeatureCardProps) {
  return (
    <motion.article
      whileHover={{ y: -6, boxShadow: "0 28px 80px rgba(15,23,42,0.14)" }}
      transition={{ duration: 0.28, ease: "easeOut" }}
      className="rounded-[28px] border border-white/60 bg-white/80 p-7 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur cursor-default"
    >
      <div className={`mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} text-white`}>
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-slate-950">{title}</h3>
      <p className="mt-3 text-base leading-7 text-slate-600">{description}</p>
    </motion.article>
  );
}