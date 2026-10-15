"""百々かさゝぎ's animation clips, written as code (c3d/anim.py; axes in rigging.py: +X bends forward
/ lifts a limb forward / bends an elbow, -X bends a knee, +Y turns to her left, +Z leans to her right;
'<bone>@loc' is a world-axis offset: x her left, y back, z up). Arms are posed by direction (A.aim)
from the rest pose (the art's resting pose, A_01: elbows out, forearms across the front).

Her character drives the motion (docs/design/characters.md): outwardly proper and still (hands
clasped in front, small economical steps, never a symmetric A-pose), inwardly a prankster (the idle
fidgets, the grin, the hop). Chibi bodies move in bigger arcs than real ones: a step is a bounce, a
stop overshoots, the head leads a turn. Secondary motion (hair, the sleeves' bags, the haori's
panels, the sash's tails, the hat's cords) is NOT animated here: SpringBoneSimulator3D does it in the
game, so it always answers what she really does (turns, stops, wind).

Locomotion clips are in place (no root motion): the game moves her and plays walk / run at the
speed she really moves (rig.json gives each cycle's metres per loop).
"""
import math
from mathutils import Vector
from c3d import anim as A

TAU = 2 * math.pi
P = {}            # the base poses, made from the armature by init_poses()


def bump(t, c, w):
    """Smooth periodic bump: 1 at phase c, 0 beyond +-w (phases in cycles)."""
    d = abs(((t - c + 0.5) % 1.0) - 0.5)
    if d >= w:
        return 0.0
    x = d / w
    return 0.5 * (1 + math.cos(math.pi * x))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def both(bone, rx, ry, rz, order=None):
    """A symmetric pair: the left values and the mirrored right ones."""
    o = (order,) if order else ()
    return {bone + '_L': (rx, ry, rz) + o, bone + '_R': (rx, -ry, -rz) + o}


def _mx(v):
    return Vector((-v[0], v[1], v[2]))


def arms(arm, left=None, right=None, base=None):
    """Aims the arms: left = [(bone, direction), ...] for her left arm (x her left, -y forward, z up);
    the right arm mirrors it unless given its own list. An arm given nothing (left=None with a right
    list) stays in the rest pose (the clasp)."""
    chain = []
    if left is not None:
        for bone, d in left:
            chain.append((bone + '_L', Vector(d), 0))
        if right is None:
            right = [(b, _mx(d)) for b, d in left]
    if right is not None:
        for bone, d in right:
            chain.append((bone + '_R', Vector(d), 0))
    # the tamoto's chain keeps hanging the way it hangs at rest, whatever the forearm does (the
    # springs add the swing in the game)
    for sx in ('L', 'R'):
        for k in range(2):
            b = arm.data.bones.get('sleeve_%s_%d' % (sx, k))
            if b is not None:
                chain.append((b.name, (b.tail_local - b.head_local).normalized(), 0))
    return A.aim(arm, chain, base=base)


def init_poses(arm):
    P['stand'] = arms(arm, [('upper_arm', (0.30, 0.04, -1)), ('forearm', (0.16, -0.20, -1)),
                            ('hand', (0.10, -0.25, -1))])
    # A_01: the hands loosely clasped below the obi, elbows out: the rest pose itself
    P['clasp'] = arms(arm)
    # the innocent prankster: hands behind her back
    P['behind'] = arms(arm, [('upper_arm', (0.26, 0.40, -1)), ('forearm', (-0.75, 0.45, -0.45)),
                             ('hand', (-0.85, 0.30, -0.35))])
    # cheering: arms flung up and out (a V)
    P['arms_up'] = arms(arm, [('upper_arm', (0.62, -0.15, 0.80)), ('forearm', (0.42, -0.18, 1.0)),
                              ('hand', (0.35, -0.12, 1.0))])
    # her right hand up to the hat's brim, the left still at her waist
    P['hat_touch'] = arms(arm, right=[('upper_arm', (-0.62, -0.62, 0.22)), ('forearm', (0.22, -0.30, 1.0)),
                                      ('hand', (0.30, -0.40, 0.9))])
    # a wave with her right hand
    P['wave'] = arms(arm, right=[('upper_arm', (-0.95, -0.30, 0.12)), ('forearm', (-0.50, -0.30, 0.85)),
                                 ('hand', (-0.45, -0.28, 0.9))])
    # fists down at her sides, a little back (the pout)
    P['fists'] = arms(arm, [('upper_arm', (0.18, 0.18, -1)), ('forearm', (0.10, 0.10, -1)),
                            ('hand', (0.06, 0.10, -1))])
    # running: elbows bent, hands forward
    P['run_arms'] = arms(arm, [('upper_arm', (0.28, 0.10, -1)), ('forearm', (0.0, -1.0, -0.25)),
                               ('hand', (0.0, -1.0, -0.1))])
    # hands in the lap (seiza)
    P['lap'] = arms(arm, [('upper_arm', (0.25, -0.30, -1)), ('forearm', (-0.35, -0.85, -0.25)),
                          ('hand', (-0.4, -0.8, -0.35))])
    # climbing: both hands up the trunk, and the grip lower down
    P['reach'] = arms(arm, [('upper_arm', (0.22, -0.55, 1.0)), ('forearm', (0.05, -0.45, 1.0)),
                            ('hand', (0.0, -0.4, 1.0))])
    P['grip'] = arms(arm, [('upper_arm', (0.30, -0.80, 0.25)), ('forearm', (-0.10, -0.55, 0.85)),
                           ('hand', (-0.1, -0.5, 0.85))])
    return P


# ------------------------------------------------------------------------------------------------
# cycles

WALK_FRAMES = 18          # two steps
WALK_SPEED = 1.5          # m/s that the cycle's feet match (0.9 m a loop)
RUN_FRAMES = 12
RUN_SPEED = 3.6
HEAVY_FRAMES = 26
HEAVY_SPEED = 0.95


def legs_walk(t, heavy=0.0, stride=19.0):
    p = {}
    for side, ph in (('L', 0.0), ('R', 0.5)):
        tt = (t + ph) % 1.0
        cc = math.cos(TAU * tt)
        thigh = stride * cc + 3.0 + 8.0 * heavy
        knee = -(4.0 + 14.0 * bump(tt, 0.13, 0.13) + 52.0 * bump(tt, 0.76, 0.2)) - 10.0 * heavy
        foot = 14.0 * bump(tt, 0.0, 0.1) - 22.0 * bump(tt, 0.55, 0.1) + 8.0 * bump(tt, 0.8, 0.12)
        p['thigh_' + side] = (thigh, 0, 0)
        p['shin_' + side] = (knee, 0, 0)
        p['foot_' + side] = (foot, 0, 0)
        p['toe_' + side] = (18.0 * bump(tt, 0.55, 0.1), 0, 0)
    return p


def walk_pose(t, heavy=0.0):
    c = math.cos(TAU * t)
    p = legs_walk(t, heavy, stride=19.0 * (1 - 0.35 * heavy))
    # arms: swing against the legs from a relaxed hang; the forearm lags (bends coming forward)
    arm_p = dict(P['stand'])
    for side, ph in (('L', 0.0), ('R', 0.5)):
        cc = math.cos(TAU * ((t + ph) % 1.0))
        sw = -14.0 * cc * (1 - 0.5 * heavy)
        arm_p = A.add_pose(arm_p, {'upper_arm_' + side: (sw, 0, 0),
                                   'forearm_' + side: (8.0 + 9.0 * max(0.0, -cc) + 25.0 * heavy, 0, 0)})
    p.update(arm_p)
    # the body: a springy bob (lowest just after each contact), a sway over the standing foot,
    # pelvis and shoulders twisting against each other, the head kept level
    bob = 0.016 * math.cos(2 * TAU * (t - 0.25)) - 0.004 - 0.02 * heavy
    sway = 0.010 * math.cos(TAU * (t - 0.25))
    p['hips@loc'] = (sway, 0.0, bob)
    p['hips'] = (2.0 + 4.0 * heavy, -6.0 * c, 3.0 * math.sin(TAU * t))
    p['spine'] = (3.0 + 8.0 * heavy, 4.0 * c, -1.5 * math.sin(TAU * t))
    p['chest'] = (1.0 + 6.0 * heavy, 4.0 * c, 0)
    p['neck'] = (-1.0, -2.0 * c, 0)
    p['head'] = (-2.0 - 6.0 * heavy - 2.0 * math.cos(2 * TAU * (t - 0.3)), 0, -1.5 * math.sin(TAU * t))
    return p


def run_pose(t):
    p = {}
    for side, ph in (('L', 0.0), ('R', 0.5)):
        tt = (t + ph) % 1.0
        cc = math.cos(TAU * tt)
        thigh = 36.0 * cc + 8.0 + 14.0 * bump(tt, 0.85, 0.15)
        knee = -(16.0 + 20.0 * bump(tt, 0.12, 0.12) + 92.0 * bump(tt, 0.72, 0.24))
        foot = 10.0 * bump(tt, 0.0, 0.08) - 30.0 * bump(tt, 0.42, 0.1) + 12.0 * bump(tt, 0.75, 0.12)
        p['thigh_' + side] = (thigh, 0, 0)
        p['shin_' + side] = (knee, 0, 0)
        p['foot_' + side] = (foot, 0, 0)
        p['toe_' + side] = (24.0 * bump(tt, 0.42, 0.1), 0, 0)
    arm_p = dict(P['run_arms'])
    for side, ph in (('L', 0.0), ('R', 0.5)):
        cc = math.cos(TAU * ((t + ph) % 1.0))
        arm_p = A.add_pose(arm_p, {'upper_arm_' + side: (-30.0 * cc, 0, 0)})
    p.update(arm_p)
    bob = 0.030 * math.cos(2 * TAU * (t - 0.40)) + 0.004
    p['hips@loc'] = (0.012 * math.cos(TAU * (t - 0.2)), 0.0, bob)
    c = math.cos(TAU * t)
    p['hips'] = (6.0, -9.0 * c, 3.0 * math.sin(TAU * t))
    p['spine'] = (8.0, 6.0 * c, 0)
    p['chest'] = (4.0, 6.0 * c, 0)
    p['neck'] = (-4.0, -3.0 * c, 0)
    p['head'] = (-6.0 - 3.0 * math.cos(2 * TAU * (t - 0.45)), 0, 0)
    return p


def stance():
    """Her weight on her left leg (contrapposto): the left hip up, the right knee soft and its foot a
    little forward and out, the shoulders tilted against the hips, the head tipped toward her right
    shoulder (tipped, not turned). The base of every standing pose: never a symmetric A."""
    return {
        'hips@loc': (0.020, 0.0, -0.006),
        'hips': (0, 2, 5),
        'spine': (1, -2, -3),
        'chest': (0, -1, -3),
        'neck': (0, 0, 2),
        'head': (-2, 0, 8),     # tipped, not turned: turned, her profile showed only hair
        'thigh_L': (0, 0, -5),
        'shin_L': (-1, 0, 0),
        'foot_L': (0, 0, 2),
        'thigh_R': (9, 0, -7),
        'shin_R': (-17, 0, 0),
        'foot_R': (10, 0, 3),
    }


def standing(*extra):
    return A.add_pose(P['clasp'], stance(), *extra)


def idle_pose(t):
    """Four seconds of standing: breath (twice), the weight easing a little over the standing leg, the
    head drifting. Each breath lifts her chest and head by one native pixel (a pixel-art idle's
    bob: 0.034 m = 1 px; the feet stay planted, the torso stretches a little): smaller, it never
    reached the screen and she stood frozen between the idle variants."""
    br = math.sin(TAU * 2 * t)
    sh = math.sin(TAU * t)
    return standing({
        'hips@loc': (0.006 * sh, 0.0, 0.0),
        'chest@loc': (0.0, 0.0, 0.034 * (0.5 + 0.5 * br)),
        'hips': (0, 0, 1.2 * sh),
        'spine': (0, 0, -1.0 * sh),
        'chest': (-1.6 * br, 0, 0),
        'neck': (0.6 * br, 0, 0),
        'head': (1.0 * math.sin(TAU * t + 1.0), 3.0 * math.sin(TAU * t + 2.0), 1.5 * sh),
        'shoulder_L': (0, 0, -1.2 * br),
        'shoulder_R': (0, 0, 1.2 * br),
    })


def heavy_pose(t):
    p = walk_pose(t, heavy=1.0)
    st = bump(t, 0.03, 0.06) + bump(t, 0.53, 0.06)
    p['hips@loc'] = (p['hips@loc'][0], 0.0, p['hips@loc'][2] - 0.018 * st)
    p['spine'] = (p['spine'][0] + 6.0, p['spine'][1], p['spine'][2])
    p['head'] = (8.0, 0, p['head'][2])
    return p


def turn_step_pose(t):
    """Small stepping on the spot while she turns."""
    p = dict(P['clasp'])
    for side, ph in (('L', 0.0), ('R', 0.5)):
        tt = (t + ph) % 1.0
        lift = bump(tt, 0.25, 0.25)
        p['thigh_' + side] = (22.0 * lift, 0, 0)
        p['shin_' + side] = (-40.0 * lift, 0, 0)
        p['foot_' + side] = (10.0 * lift, 0, 0)
    p['hips@loc'] = (0.0, 0.0, -0.01 * (bump(t, 0.0, 0.2) + bump(t, 0.5, 0.2)))
    return p


# ------------------------------------------------------------------------------------------------
# key-pose clips

def _keys(arm, name, frames, keys, loop=False):
    c = A.Clip(arm, name, frames, loop=loop)
    for f, pose in keys:
        c.key(f, pose)
    return c.finish()


def clip_stop(arm):
    # the body carries on a little past the feet, comes back, settles into her stance
    k = [(0, A.add_pose(P['stand'], {'spine': (8, 0, 0), 'chest': (4, 0, 0), 'hips@loc': (0, 0, -0.01)})),
         (4, A.add_pose(P['stand'], {'spine': (12, 0, 0), 'chest': (6, 0, 0), 'head': (4, 0, 0),
                                     'hips@loc': (0, 0, -0.022), **both('upper_arm', 26, 0, 0),
                                     **both('thigh', 8, 0, 0), **both('shin', -18, 0, 0), **both('foot', 10, 0, 0)})),
         (10, A.add_pose(P['stand'], {'spine': (-3, 0, 0), 'head': (-3, 0, 0), 'hips@loc': (0, 0, 0.004),
                                      **both('upper_arm', -6, 0, 0)})),
         (18, standing())]
    return _keys(arm, 'stop', 18, k)


def clip_look(arm):
    """東張西望: looks to her left, holds, a quick glance right, back (3 s)."""
    k = [(0, standing()),
         (10, standing({'head': (-6, 30, -6), 'neck': (0, 8, 0), 'chest': (0, 8, 0)})),
         (34, standing({'head': (-8, 33, -8), 'neck': (0, 8, 0), 'chest': (0, 9, 0)})),
         (42, standing({'head': (-2, -12, 0), 'chest': (0, -2, 0)})),
         (50, standing({'head': (-4, -48, 4), 'neck': (0, -8, 0), 'chest': (0, -9, 0)})),
         (72, standing({'head': (-6, -46, 2), 'neck': (0, -8, 0), 'chest': (0, -8, 0)})),
         (90, standing())]
    return _keys(arm, 'idle_look', 90, k)


def clip_sway(arm):
    """The prankster at rest: hands behind her back, she rocks heel to toe and side to side, the head
    tipping with the rhythm, as if humming (3.2 s, loops)."""
    def fn(t):
        s = math.sin(TAU * 2 * t)
        r = math.sin(TAU * t)
        return A.add_pose(P['behind'], stance(), {
            'hips@loc': (0.012 * r - 0.01, 0.0, 0.006 * max(0.0, s)),
            'hips': (0, 0, -3.0 * r - 3),
            'spine': (-3.0, 0, 3.0 * r),
            'chest': (-2.0, 4.0 * r, 0),
            'head': (-4.0, 6.0 * r - 4, 9.0 * r - 6),
            **both('foot', -10.0 * max(0.0, s), 0, 0),
            **both('toe', 12.0 * max(0.0, s), 0, 0),
        })
    c = A.Clip(arm, 'idle_sway', 96, loop=True)
    c.sample(fn, step=4)
    return c.finish()


def clip_hat(arm):
    """摸笠沿: her right hand goes up to the brim and tips it up; she peers up from under it, grins,
    and lets it go (2.6 s). (The hat's own tilt is the game's; the 'hat' bone here is a small extra
    tip on top of it.)"""
    up = A.add_pose(P['hat_touch'], stance())
    k = [(0, standing()),
         (10, A.add_pose(up, {'head': (-8, 6, 2), 'chest': (-3, 4, 0)})),
         (16, A.add_pose(up, {'head': (-10, 8, -2), 'chest': (-4, 4, 0), 'hat': (-6, 0, 0)})),
         (52, A.add_pose(up, {'head': (-9, 10, -4), 'chest': (-4, 5, 0), 'hat': (-6, 0, 0)})),
         (64, standing({'head': (-4, 2, 0)})),
         (78, standing())]
    return _keys(arm, 'idle_hat', 78, k)


def clip_tilt(arm):
    """歪头: a curious head tilt the other way, with a little lean (1.6 s)."""
    k = [(0, standing()),
         (6, standing({'head': (-4, -4, -30), 'neck': (0, 0, -6), 'chest': (0, 0, 4), 'hips@loc': (-0.01, 0, 0)})),
         (36, standing({'head': (-5, -6, -32), 'neck': (0, 0, -6), 'chest': (0, 0, 4), 'hips@loc': (-0.01, 0, 0)})),
         (48, standing())]
    return _keys(arm, 'tilt', 48, k)


def clip_pout(arm):
    """鼓腮: fists down by her sides, shoulders up, chin turned away, one little stomp (2 s)."""
    f = P['fists']
    k = [(0, standing()),
         (6, A.add_pose(f, {'shoulder_L': (0, 0, -8), 'shoulder_R': (0, 0, 8), 'head': (6, -26, -6),
                            'chest': (-3, -6, 0), 'thigh_R': (24, 0, 0), 'shin_R': (-40, 0, 0)})),
         (10, A.add_pose(f, {'shoulder_L': (0, 0, -8), 'shoulder_R': (0, 0, 8), 'head': (8, -28, -6),
                             'chest': (-3, -6, 0), 'hips@loc': (0, 0, -0.012)})),
         (48, A.add_pose(f, {'shoulder_L': (0, 0, -6), 'shoulder_R': (0, 0, 6), 'head': (8, -30, -8),
                             'chest': (-3, -7, 0)})),
         (60, standing())]
    return _keys(arm, 'pout', 60, k)


def clip_cheer(arm):
    """欢呼: a crouch, a hop with both arms flung up, landing, arms down (1.7 s)."""
    crouch = A.add_pose(P['stand'], {'hips@loc': (0, 0, -0.07), **both('thigh', 30, 0, 0), **both('shin', -58, 0, 0),
                                     **both('foot', 26, 0, 0), 'spine': (10, 0, 0), **both('upper_arm', -20, 0, 0)})
    up = A.add_pose(P['arms_up'], {'hips@loc': (0, 0, 0.16), 'spine': (-8, 0, 0), 'head': (-14, 0, 0),
                                   **both('thigh', 18, 0, 0), **both('shin', -46, 0, 0), **both('foot', -20, 0, 0)})
    k = [(0, standing()), (6, crouch), (11, up),
         (20, A.add_pose(P['arms_up'], {'hips@loc': (0, 0, 0.0), 'head': (-10, 0, 0)})),
         (24, A.add_pose(P['arms_up'], {'hips@loc': (0, 0, -0.04), **both('thigh', 16, 0, 0), **both('shin', -30, 0, 0),
                                        **both('foot', 14, 0, 0), 'head': (-8, 0, 0)})),
         (38, A.add_pose(P['arms_up'], {'head': (-10, 0, 0)})),
         (52, standing())]
    return _keys(arm, 'cheer', 52, k)


def clip_sigh(arm):
    """叹气: a breath in (shoulders up, chin up), a long breath out (everything sags), and up again."""
    k = [(0, standing()),
         (14, standing({'chest': (-8, 0, 0), 'head': (-10, 0, 0), 'shoulder_L': (0, 0, -6),
                        'shoulder_R': (0, 0, 6), 'hips@loc': (0, 0, 0.006)})),
         (38, A.add_pose(P['stand'], {'spine': (10, 0, 0), 'chest': (10, 0, 0), 'head': (18, 0, 4), 'neck': (6, 0, 0),
                                      'shoulder_L': (0, 0, 6), 'shoulder_R': (0, 0, -6), 'hips@loc': (0, 0, -0.012)})),
         (56, A.add_pose(P['stand'], {'spine': (8, 0, 0), 'chest': (8, 0, 0), 'head': (16, 0, 4), 'neck': (6, 0, 0),
                                      'hips@loc': (0, 0, -0.01)})),
         (72, standing())]
    return _keys(arm, 'sigh', 72, k)


def clip_wave(arm):
    """A wave (A_02), 1.6 s: the right hand up, three swings of the forearm."""
    base = A.add_pose(P['wave'], stance(), {'head': (-4, -6, -6)})
    keys = [(0, standing())]
    for k, f in enumerate((8, 14, 20, 26, 32, 38)):
        keys.append((f, A.add_pose(base, {'forearm_R': (0, 0, 16 if k % 2 == 0 else -16)})))
    keys.append((48, standing()))
    return _keys(arm, 'wave', 48, keys)


def clip_jump(arm):
    crouch = A.add_pose(P['stand'], {'hips@loc': (0, 0, -0.085), **both('thigh', 34, 0, 0), **both('shin', -66, 0, 0),
                                     **both('foot', 30, 0, 0), 'spine': (16, 0, 0), 'head': (-6, 0, 0),
                                     **both('upper_arm', -34, 0, 0), **both('forearm', 20, 0, 0)})
    push = A.add_pose(P['stand'], {'hips@loc': (0, 0, 0.03), **both('foot', -24, 0, 0), **both('toe', 20, 0, 0),
                                   'spine': (2, 0, 0), **both('upper_arm', 60, 0, 0), **both('forearm', 30, 0, 0)})
    _keys(arm, 'jump_start', 8, [(0, P['stand']), (5, crouch), (8, push)])
    air = A.add_pose(P['arms_up'], {**both('thigh', 34, 0, 0), **both('shin', -52, 0, 0), **both('foot', 6, 0, 0),
                                    'spine': (-4, 0, 0), 'head': (-8, 0, 0)})
    air2 = A.add_pose(air, {**both('upper_arm', 8, 0, 0), 'hips@loc': (0, 0, 0.01)})
    _keys(arm, 'jump_air', 16, [(0, air), (8, air2), (16, air)], loop=True)
    land = A.add_pose(P['stand'], {'hips@loc': (0, 0, -0.09), **both('thigh', 36, 0, 0), **both('shin', -70, 0, 0),
                                   **both('foot', 32, 0, 0), 'spine': (18, 0, 0), 'head': (4, 0, 0),
                                   **both('upper_arm', 30, 0, 0), **both('forearm', 26, 0, 0)})
    _keys(arm, 'jump_land', 14, [(0, air), (2, land), (7, A.add_pose(land, {'hips@loc': (0, 0, 0.03)})),
                                 (14, standing())])


def clip_climb(arm):
    """Climbing a trunk (she faces it): arms reach up in turn, the opposite knee steps up and pushes;
    in place, the game lifts her 0.5 m a loop."""
    def fn(t):
        p = {}
        for side, ph in (('L', 0.0), ('R', 0.5)):
            tt = (t + ph) % 1.0
            reach = ease(min(1.0, tt / 0.35)) * (1 - ease((tt - 0.5) / 0.5))
            g = {k: v for k, v in A.lerp_pose(P['grip'], P['reach'], reach).items()
                 if k.endswith('_' + side) or ('_%s_' % side) in k}
            p.update(g)
            step = bump(tt, 0.75, 0.25)
            p['thigh_' + side] = (40 + 50 * step, 0, -6 if side == 'L' else 6)
            p['shin_' + side] = (-60 - 50 * step, 0, 0)
            p['foot_' + side] = (20, 0, 0)
        p['spine'] = (14, 0, 6 * math.sin(TAU * t))
        p['chest'] = (8, 0, 0)
        p['head'] = (-22, 0, 0)
        p['hips@loc'] = (0.01 * math.sin(TAU * t), -0.06, 0.02 * math.cos(2 * TAU * t))
        return p
    c = A.Clip(arm, 'climb', 30, loop=True)
    c.sample(fn, step=2)
    return c.finish()


def seiza():
    return A.add_pose(P['lap'], {'hips@loc': (0, 0.04, -0.40), 'hips': (-6, 0, 0), 'spine': (4, 0, 0),
                                 'chest': (2, 0, 0), **both('thigh', 92, 0, -4), **both('shin', -165, 0, 0),
                                 **both('foot', -40, 0, 0)})


def clip_sit(arm):
    """Seiza (A_18): she kneels, sits back on her heels, hands in her lap; and up again."""
    sz = seiza()
    half = A.add_pose(P['lap'], {'hips@loc': (0, 0.02, -0.22), 'spine': (22, 0, 0), 'head': (-8, 0, 0),
                                 **both('thigh', 70, 0, -4), **both('shin', -110, 0, 0), **both('foot', 20, 0, 0)})
    _keys(arm, 'sit_down', 26, [(0, standing()), (12, half), (26, sz)])

    def fn(t):
        br = math.sin(TAU * t * 2)
        return A.add_pose(sz, {'chest': (-1.5 * br, 0, 0),
                               'head': (1.0 * math.sin(TAU * t), 4 * math.sin(TAU * t + 1), 2 * math.sin(TAU * t))})
    c = A.Clip(arm, 'sit_idle', 90, loop=True)
    c.sample(fn, step=6)
    c.finish()
    _keys(arm, 'stand_up', 24, [(0, sz), (12, half), (24, standing())])


def build_all(arm):
    init_poses(arm)
    c = A.Clip(arm, 'idle', 120, loop=True)
    c.sample(idle_pose, step=6)
    c.finish()
    c = A.Clip(arm, 'walk', WALK_FRAMES, loop=True)
    c.sample(walk_pose, step=1)
    c.finish()
    c = A.Clip(arm, 'run', RUN_FRAMES, loop=True)
    c.sample(run_pose, step=1)
    c.finish()
    c = A.Clip(arm, 'heavy_walk', HEAVY_FRAMES, loop=True)
    c.sample(heavy_pose, step=1)
    c.finish()
    c = A.Clip(arm, 'turn_step', 12, loop=True)
    c.sample(turn_step_pose, step=1)
    c.finish()
    clip_stop(arm)
    clip_look(arm)
    clip_sway(arm)
    clip_hat(arm)
    clip_tilt(arm)
    clip_pout(arm)
    clip_cheer(arm)
    clip_sigh(arm)
    clip_wave(arm)
    clip_jump(arm)
    clip_climb(arm)
    clip_sit(arm)


CLIP_INFO = {
    # loops and the ground speed (m/s) at which the feet do not slide
    'idle': {'loop': True}, 'walk': {'loop': True, 'speed': WALK_SPEED}, 'run': {'loop': True, 'speed': RUN_SPEED},
    'heavy_walk': {'loop': True, 'speed': HEAVY_SPEED}, 'turn_step': {'loop': True}, 'idle_sway': {'loop': True},
    'jump_air': {'loop': True}, 'climb': {'loop': True, 'rise': 0.5}, 'sit_idle': {'loop': True},
}


def pose_at(arm, name, frame):
    """A pose for previews, evaluated from the code."""
    if not P:
        init_poses(arm)
    if name == 'walk':
        return walk_pose((frame % WALK_FRAMES) / WALK_FRAMES)
    if name == 'run':
        return run_pose((frame % RUN_FRAMES) / RUN_FRAMES)
    if name == 'heavy_walk':
        return heavy_pose((frame % HEAVY_FRAMES) / HEAVY_FRAMES)
    if name == 'idle':
        return idle_pose((frame % 120) / 120)
    if name == 'stance':
        return standing()
    if name == 'seiza':
        return seiza()
    if name == 'rest':
        return {}
    return P.get(name, {})


def apply_pose(arm, spec):
    name, _, fr = spec.partition('@')
    A.apply_pose(arm, pose_at(arm, name, int(fr or 0)))
