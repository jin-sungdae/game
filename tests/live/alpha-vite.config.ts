import {defineConfig} from 'vite';
import {resolve} from 'node:path';
export default defineConfig({build:{outDir:process.env.LUMA_ALPHA_WEB_OUT ?? '/tmp/luma-alpha-web',emptyOutDir:true,rollupOptions:{input:resolve('tests/live/alpha.html')}}});
