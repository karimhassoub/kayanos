import frappeUIPreset from "frappe-ui/src/tailwind/preset"

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			colors: {
				brand: {
					50: '#f0f9ff',
					100: '#e0f2fe',
					500: '#0ea5e9',
					600: '#0284c7',
					900: '#0c4a6e',
				}
			}
		},
	},
	plugins: [],
}
