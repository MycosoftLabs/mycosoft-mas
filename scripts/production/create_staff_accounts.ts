/**
 * Create Staff Accounts for MYCA
 * Run with: npx ts-node scripts/production/create_staff_accounts.ts
 */

import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import crypto from "crypto";

const prisma = new PrismaClient();

interface StaffMember {
  name: string;
  email: string;
  role: "super_admin" | "admin" | "developer" | "staff";
  generatePassword: boolean;
}

const STAFF_MEMBERS: StaffMember[] = [
  {
    name: "Morgan",
    email: "morgan@mycosoft.com",
    role: "super_admin",
    generatePassword: false, // Uses Google OAuth
  },
  {
    name: "Alberto",
    email: "alberto@mycosoft.com",
    role: "admin",
    generatePassword: true,
  },
  {
    name: "Garrett",
    email: "garrett@mycosoft.com",
    role: "admin",
    generatePassword: true,
  },
  {
    name: "Abelardo",
    email: "abelardo@mycosoft.com",
    role: "developer",
    generatePassword: true,
  },
  {
    name: "RJ",
    email: "rj@mycosoft.com",
    role: "developer",
    generatePassword: true,
  },
  {
    name: "Chris",
    email: "chris@mycosoft.com",
    role: "developer",
    generatePassword: true,
  },
];

function generateSecurePassword(): string {
  return crypto.randomBytes(16).toString("base64").slice(0, 20);
}

async function createStaffAccounts() {
  console.log("================================================");
  console.log("  Creating Staff Accounts");
  console.log("================================================\n");

  const results: { email: string; password?: string; status: string }[] = [];

  for (const member of STAFF_MEMBERS) {
    console.log(`Processing: ${member.name} (${member.email})...`);

    try {
      // Check if user exists
      const existing = await prisma.user.findUnique({
        where: { email: member.email },
      });

      if (existing) {
        console.log(`  Already exists, updating role...`);
        await prisma.user.update({
          where: { email: member.email },
          data: { role: member.role },
        });
        results.push({ email: member.email, status: "Updated" });
        continue;
      }

      // Generate password if needed
      let password: string | undefined;
      let hashedPassword: string | undefined;

      if (member.generatePassword) {
        password = generateSecurePassword();
        hashedPassword = await bcrypt.hash(password, 12);
      }

      // Create user
      await prisma.user.create({
        data: {
          name: member.name,
          email: member.email,
          role: member.role,
          password: hashedPassword,
          emailVerified: new Date(), // Pre-verified for staff
        },
      });

      console.log(`  Created successfully`);
      results.push({
        email: member.email,
        password: password,
        status: "Created",
      });
    } catch (error) {
      console.error(`  Error: ${error}`);
      results.push({ email: member.email, status: `Error: ${error}` });
    }
  }

  // Summary
  console.log("\n================================================");
  console.log("  Summary");
  console.log("================================================\n");

  console.log("Staff Accounts:\n");
  for (const result of results) {
    console.log(`  ${result.email}`);
    console.log(`    Status: ${result.status}`);
    if (result.password) {
      console.log(`    Temp Password: ${result.password}`);
      console.log(`    (Send securely to user, they should change on first login)`);
    }
    console.log("");
  }

  console.log("================================================");
  console.log("  IMPORTANT: Save passwords securely!");
  console.log("  Users should change passwords on first login.");
  console.log("  Prefer Google OAuth for daily use.");
  console.log("================================================\n");
}

async function main() {
  try {
    await createStaffAccounts();
  } catch (error) {
    console.error("Failed to create staff accounts:", error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
