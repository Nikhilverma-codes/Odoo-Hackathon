export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email: string): boolean {
	return EMAIL_PATTERN.test(email.trim());
}

export function passwordIssues(password: string): string[] {
	const issues: string[] = [];
	if (password.length <= 8) issues.push('Use more than 8 characters');
	if (!/[A-Z]/.test(password)) issues.push('Add an uppercase letter');
	if (!/[a-z]/.test(password)) issues.push('Add a lowercase letter');
	if (!/[^A-Za-z0-9]/.test(password)) issues.push('Add a special character');
	return issues;
}

export function isStrongPassword(password: string): boolean {
	return passwordIssues(password).length === 0;
}

let counter = 0;

export function uid(prefix: string): string {
	return `${prefix}_${Date.now().toString(36)}${(counter++).toString(36)}${Math.random()
		.toString(36)
		.slice(2, 5)}`;
}
