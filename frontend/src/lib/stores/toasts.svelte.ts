export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
	id: number;
	type: ToastType;
	message: string;
}

let sequence = 0;
let items = $state<Toast[]>([]);

export const toasts = {
	get items(): Toast[] {
		return items;
	},
	push(message: string, type: ToastType = 'success') {
		const id = ++sequence;
		items = [...items, { id, type, message }];
		setTimeout(() => toasts.dismiss(id), 4000);
	},
	success(message: string) {
		toasts.push(message, 'success');
	},
	error(message: string) {
		toasts.push(message, 'error');
	},
	info(message: string) {
		toasts.push(message, 'info');
	},
	dismiss(id: number) {
		items = items.filter((toast) => toast.id !== id);
	}
};
