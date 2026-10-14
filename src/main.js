// Entry: the playable gray box; ?view=render shows the render foundation's test scene alone.
import { params } from './core/params.js';

if (params.view === 'render') import('./render-test.js');
else import('./play/main.js');
