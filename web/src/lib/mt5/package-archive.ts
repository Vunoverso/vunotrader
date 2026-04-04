import { promises as fs } from "fs";
import path from "path";
import JSZip from "jszip";

import {
  buildQuickStart,
  buildRuntimeConfig,
  resolvePackageTemplateRoot,
  type RobotPackageInput,
} from "@/lib/mt5/package-template";

const SKIPPED_FILES = new Set(["LEIA-PRIMEIRO.txt", "agent-local/runtime/config.json"]);

function normalizeZipPath(value: string): string {
  return value.replace(/\\/g, "/");
}

async function assertDirectoryExists(dirPath: string): Promise<void> {
  const stats = await fs.stat(dirPath).catch(() => null);
  if (!stats?.isDirectory()) {
    throw new Error(`Diretorio de template nao encontrado: ${dirPath}`);
  }
}

async function appendDirectory(zip: JSZip, sourceDir: string, targetDir: string): Promise<void> {
  const entries = await fs.readdir(sourceDir, { withFileTypes: true });

  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = normalizeZipPath(path.posix.join(targetDir, entry.name));

    if (SKIPPED_FILES.has(targetPath)) {
      continue;
    }

    if (entry.isDirectory()) {
      await appendDirectory(zip, sourcePath, targetPath);
      continue;
    }

    zip.file(targetPath, await fs.readFile(sourcePath));
  }
}

export async function buildRobotPackageBuffer(input: RobotPackageInput): Promise<Buffer> {
  const templateRoot = resolvePackageTemplateRoot();
  const zip = new JSZip();

  await assertDirectoryExists(templateRoot);
  await appendDirectory(zip, path.join(templateRoot, "agent-local"), "agent-local");
  await appendDirectory(zip, path.join(templateRoot, "mt5"), "mt5");

  zip.file("LEIA-PRIMEIRO.txt", buildQuickStart(input));
  zip.file("agent-local/runtime/config.json", buildRuntimeConfig(input));

  return zip.generateAsync({
    type: "nodebuffer",
    compression: "DEFLATE",
    compressionOptions: { level: 6 },
  });
}