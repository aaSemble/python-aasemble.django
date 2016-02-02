import logging
import os
import os.path

from django.template.loader import render_to_string

LOG = logging.getLogger(__name__)


def recursive_render(src, dst, context, logger=LOG):
    logger.debug('Processing %s' % (src,))
    if os.path.isdir(src):
        if not os.path.isdir(dst):
            os.mkdir(dst)
        for f in os.listdir(src):
            recursive_render(os.path.join(src, f), os.path.join(dst, f), context)
    else:
        if src.endswith('.swp'):
            return
        logger.debug('Rendering %s' % (src,))
        s = render_to_string(src, context)
        logger.debug('Result: %r' % (s,))
        with open(dst, 'w') as fp_out:
            fp_out.write(s)
