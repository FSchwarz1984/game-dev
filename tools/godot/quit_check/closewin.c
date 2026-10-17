/* closewin <window id>: ask a window to close the way a window manager does (WM_DELETE_WINDOW),
   for testing the game's quit through the window's close button on an X server without a WM. */
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv) {
	if (argc < 2) { fprintf(stderr, "usage: closewin <window id>\n"); return 2; }
	Display *d = XOpenDisplay(NULL);
	if (!d) { fprintf(stderr, "no display\n"); return 1; }
	Window w = (Window)strtoul(argv[1], NULL, 0);
	/* the atoms must exist before the game starts (a window manager makes them; Xvfb has none, and
	   the engine looks them up with only_if_exists): "closewin 0" only makes them */
	Atom protocols = XInternAtom(d, "WM_PROTOCOLS", False);
	Atom del = XInternAtom(d, "WM_DELETE_WINDOW", False);
	if (w == 0) { XCloseDisplay(d); return 0; }
	XEvent e;
	memset(&e, 0, sizeof(e));
	e.xclient.type = ClientMessage;
	e.xclient.window = w;
	e.xclient.message_type = protocols;
	e.xclient.format = 32;
	e.xclient.data.l[0] = del;
	e.xclient.data.l[1] = CurrentTime;
	XSendEvent(d, w, False, NoEventMask, &e);
	XFlush(d);
	XCloseDisplay(d);
	return 0;
}
