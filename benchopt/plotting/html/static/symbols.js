/**
 * Round with precision control
 * https://github.com/plotly/d3/blob/6bb40cd42f6479be84efda3e50c8444b50d5905d/d3.js#L2189
 */
const d3round = (x, n) => {
    return n ? Math.round(x * (n = Math.pow(10, n))) / n : Math.round(x);
};

/**
 * Container of function that create path for SVG plot marker
 * https://github.com/plotly/plotly.js/blob/b2df3710d7877ff5b4f85256015a88c8ea8fbe1d/src/components/drawing/symbol_defs.js#L13
 */
const SYMBOLDEFS = {
    circle: {
        n: 0,
        f: r => {
            var rs = d3round(r, 2);
            return 'M' + rs + ',0A' + rs + ',' + rs + ' 0 1,1 0,-' + rs +
                'A' + rs + ',' + rs + ' 0 0,1 ' + rs + ',0Z';
        }
    },
    square: {
        n: 1,
        f: r => {
            var rs = d3round(r, 2);
            return 'M' + rs + ',' + rs + 'H-' + rs + 'V-' + rs + 'H' + rs + 'Z';
        }
    },
    diamond: {
        n: 2,
        f: r => {
            var rd = d3round(r * 1.3, 2);
            return 'M' + rd + ',0L0,' + rd + 'L-' + rd + ',0L0,-' + rd + 'Z';
        }
    },
    cross: {
        n: 3,
        f: r => {
            var rc = d3round(r * 0.4, 2);
            var rc2 = d3round(r * 1.2, 2);
            return 'M' + rc2 + ',' + rc + 'H' + rc + 'V' + rc2 + 'H-' + rc +
                'V' + rc + 'H-' + rc2 + 'V-' + rc + 'H-' + rc + 'V-' + rc2 +
                'H' + rc + 'V-' + rc + 'H' + rc2 + 'Z';
        }
    },
    x: {
        n: 4,
        f: r => {
            var rx = d3round(r * 0.8 / Math.sqrt(2), 2);
            var ne = 'l' + rx + ',' + rx;
            var se = 'l' + rx + ',-' + rx;
            var sw = 'l-' + rx + ',-' + rx;
            var nw = 'l-' + rx + ',' + rx;
            return 'M0,' + rx + ne + se + sw + se + sw + nw + sw + nw + ne + nw + ne + 'Z';
        }
    },
    'triangle-up': {
        n: 5,
        f: r => {
            var rt = d3round(r * 2 / Math.sqrt(3), 2);
            var r2 = d3round(r / 2, 2);
            var rs = d3round(r, 2);
            return 'M-' + rt + ',' + r2 + 'H' + rt + 'L0,-' + rs + 'Z';
        }
    },
    'triangle-down': {
        n: 6,
        f: r => {
            var rt = d3round(r * 2 / Math.sqrt(3), 2);
            var r2 = d3round(r / 2, 2);
            var rs = d3round(r, 2);
            return 'M-' + rt + ',-' + r2 + 'H' + rt + 'L0,' + rs + 'Z';
        }
    },
    'triangle-left': {
        n: 7,
        f: r => {
            var rt = d3round(r * 2 / Math.sqrt(3), 2);
            var r2 = d3round(r / 2, 2);
            var rs = d3round(r, 2);
            return 'M' + r2 + ',-' + rt + 'V' + rt + 'L-' + rs + ',0Z';
        }
    },
    'triangle-right': {
        n: 8,
        f: r => {
            var rt = d3round(r * 2 / Math.sqrt(3), 2);
            var r2 = d3round(r / 2, 2);
            var rs = d3round(r, 2);
            return 'M-' + r2 + ',-' + rt + 'V' + rt + 'L' + rs + ',0Z';
        }
    },
    'triangle-ne': {
        n: 9,
        f: r => {
            var r1 = d3round(r * 0.6, 2);
            var r2 = d3round(r * 1.2, 2);
            return 'M-' + r2 + ',-' + r1 + 'H' + r1 + 'V' + r2 + 'Z';
        }
    },
    'triangle-se': {
        n: 10,
        f: r => {
            var r1 = d3round(r * 0.6, 2);
            var r2 = d3round(r * 1.2, 2);
            return 'M' + r1 + ',-' + r2 + 'V' + r1 + 'H-' + r2 + 'Z';
        }
    },
    'triangle-sw': {
        n: 11,
        f: r => {
            var r1 = d3round(r * 0.6, 2);
            var r2 = d3round(r * 1.2, 2);
            return 'M' + r2 + ',' + r1 + 'H-' + r1 + 'V-' + r2 + 'Z';
        }
    },
    'triangle-nw': {
        n: 12,
        f: r => {
            var r1 = d3round(r * 0.6, 2);
            var r2 = d3round(r * 1.2, 2);
            return 'M-' + r1 + ',' + r2 + 'V-' + r1 + 'H' + r2 + 'Z';
        }
    },
    pentagon: {
        n: 13,
        f: r => {
            var x1 = d3round(r * 0.951, 2);
            var x2 = d3round(r * 0.588, 2);
            var y0 = d3round(-r, 2);
            var y1 = d3round(r * -0.309, 2);
            var y2 = d3round(r * 0.809, 2);
            return 'M' + x1 + ',' + y1 + 'L' + x2 + ',' + y2 + 'H-' + x2 +
                'L-' + x1 + ',' + y1 + 'L0,' + y0 + 'Z';
        }
    },
    hexagon: {
        n: 14,
        f: r => {
            var y0 = d3round(r, 2);
            var y1 = d3round(r / 2, 2);
            var x = d3round(r * Math.sqrt(3) / 2, 2);
            return 'M' + x + ',-' + y1 + 'V' + y1 + 'L0,' + y0 +
                'L-' + x + ',' + y1 + 'V-' + y1 + 'L0,-' + y0 + 'Z';
        }
    },
    hexagon2: {
        n: 15,
        f: r => {
            var x0 = d3round(r, 2);
            var x1 = d3round(r / 2, 2);
            var y = d3round(r * Math.sqrt(3) / 2, 2);
            return 'M-' + x1 + ',' + y + 'H' + x1 + 'L' + x0 +
                ',0L' + x1 + ',-' + y + 'H-' + x1 + 'L-' + x0 + ',0Z';
        }
    },
    octagon: {
        n: 16,
        f: r => {
            var a = d3round(r * 0.924, 2);
            var b = d3round(r * 0.383, 2);
            return 'M-' + b + ',-' + a + 'H' + b + 'L' + a + ',-' + b + 'V' + b +
                'L' + b + ',' + a + 'H-' + b + 'L-' + a + ',' + b + 'V-' + b + 'Z';
        }
    },
    star: {
        n: 17,
        f: r => {
            var rs = r * 1.4;
            var x1 = d3round(rs * 0.225, 2);
            var x2 = d3round(rs * 0.951, 2);
            var x3 = d3round(rs * 0.363, 2);
            var x4 = d3round(rs * 0.588, 2);
            var y0 = d3round(-rs, 2);
            var y1 = d3round(rs * -0.309, 2);
            var y3 = d3round(rs * 0.118, 2);
            var y4 = d3round(rs * 0.809, 2);
            var y5 = d3round(rs * 0.382, 2);
            return 'M' + x1 + ',' + y1 + 'H' + x2 + 'L' + x3 + ',' + y3 +
                'L' + x4 + ',' + y4 + 'L0,' + y5 + 'L-' + x4 + ',' + y4 +
                'L-' + x3 + ',' + y3 + 'L-' + x2 + ',' + y1 + 'H-' + x1 +
                'L0,' + y0 + 'Z';
        }
    },
    hexagram: {
        n: 18,
        f: r => {
            var y = d3round(r * 0.66, 2);
            var x1 = d3round(r * 0.38, 2);
            var x2 = d3round(r * 0.76, 2);
            return 'M-' + x2 + ',0l-' + x1 + ',-' + y + 'h' + x2 +
                'l' + x1 + ',-' + y + 'l' + x1 + ',' + y + 'h' + x2 +
                'l-' + x1 + ',' + y + 'l' + x1 + ',' + y + 'h-' + x2 +
                'l-' + x1 + ',' + y + 'l-' + x1 + ',-' + y + 'h-' + x2 + 'Z';
        }
    },
    'star-triangle-up': {
        n: 19,
        f: r => {
            var x = d3round(r * Math.sqrt(3) * 0.8, 2);
            var y1 = d3round(r * 0.8, 2);
            var y2 = d3round(r * 1.6, 2);
            var rc = d3round(r * 4, 2);
            var aPart = 'A ' + rc + ',' + rc + ' 0 0 1 ';
            return 'M-' + x + ',' + y1 + aPart + x + ',' + y1 +
                aPart + '0,-' + y2 + aPart + '-' + x + ',' + y1 + 'Z';
        }
    },
    'star-triangle-down': {
        n: 20,
        f: r => {
            var x = d3round(r * Math.sqrt(3) * 0.8, 2);
            var y1 = d3round(r * 0.8, 2);
            var y2 = d3round(r * 1.6, 2);
            var rc = d3round(r * 4, 2);
            var aPart = 'A ' + rc + ',' + rc + ' 0 0 1 ';
            return 'M' + x + ',-' + y1 + aPart + '-' + x + ',-' + y1 +
                aPart + '0,' + y2 + aPart + x + ',-' + y1 + 'Z';
        }
    },
    'star-square': {
        n: 21,
        f: r => {
            var rp = d3round(r * 1.1, 2);
            var rc = d3round(r * 2, 2);
            var aPart = 'A ' + rc + ',' + rc + ' 0 0 1 ';
            return 'M-' + rp + ',-' + rp + aPart + '-' + rp + ',' + rp +
                aPart + rp + ',' + rp + aPart + rp + ',-' + rp +
                aPart + '-' + rp + ',-' + rp + 'Z';
        }
    },
    'star-diamond': {
        n: 22,
        f: r => {
            var rp = d3round(r * 1.4, 2);
            var rc = d3round(r * 1.9, 2);
            var aPart = 'A ' + rc + ',' + rc + ' 0 0 1 ';
            return 'M-' + rp + ',0' + aPart + '0,' + rp +
                aPart + rp + ',0' + aPart + '0,-' + rp +
                aPart + '-' + rp + ',0' + 'Z';
        }
    },
    'diamond-tall': {
        n: 23,
        f: r => {
            var x = d3round(r * 0.7, 2);
            var y = d3round(r * 1.4, 2);
            return 'M0,' + y + 'L' + x + ',0L0,-' + y + 'L-' + x + ',0Z';
        }
    },
    'diamond-wide': {
        n: 24,
        f: r => {
            var x = d3round(r * 1.4, 2);
            var y = d3round(r * 0.7, 2);
            return 'M0,' + y + 'L' + x + ',0L0,-' + y + 'L-' + x + ',0Z';
        }
    },
    hourglass: {
        n: 25,
        f: r => {
            var rs = d3round(r, 2);
            return 'M' + rs + ',' + rs + 'H-' + rs + 'L' + rs + ',-' + rs + 'H-' + rs + 'Z';
        },
        noDot: true
    },
    bowtie: {
        n: 26,
        f: r => {
            var rs = d3round(r, 2);
            return 'M' + rs + ',' + rs + 'V-' + rs + 'L-' + rs + ',' + rs + 'V-' + rs + 'Z';
        },
        noDot: true
    },
    'circle-cross': {
        n: 27,
        f: r => {
            var rs = d3round(r, 2);
            return 'M0,' + rs + 'V-' + rs + 'M' + rs + ',0H-' + rs +
                'M' + rs + ',0A' + rs + ',' + rs + ' 0 1,1 0,-' + rs +
                'A' + rs + ',' + rs + ' 0 0,1 ' + rs + ',0Z';
        },
        needLine: true,
        noDot: true
    },
    'circle-x': {
        n: 28,
        f: r => {
            var rs = d3round(r, 2);
            var rc = d3round(r / Math.sqrt(2), 2);
            return 'M' + rc + ',' + rc + 'L-' + rc + ',-' + rc +
                'M' + rc + ',-' + rc + 'L-' + rc + ',' + rc +
                'M' + rs + ',0A' + rs + ',' + rs + ' 0 1,1 0,-' + rs +
                'A' + rs + ',' + rs + ' 0 0,1 ' + rs + ',0Z';
        },
        needLine: true,
        noDot: true
    },
    'square-cross': {
        n: 29,
        f: r => {
            var rs = d3round(r, 2);
            return 'M0,' + rs + 'V-' + rs + 'M' + rs + ',0H-' + rs +
                'M' + rs + ',' + rs + 'H-' + rs + 'V-' + rs + 'H' + rs + 'Z';
        },
        needLine: true,
        noDot: true
    },
    'square-x': {
        n: 30,
        f: r => {
            var rs = d3round(r, 2);
            return 'M' + rs + ',' + rs + 'L-' + rs + ',-' + rs +
                'M' + rs + ',-' + rs + 'L-' + rs + ',' + rs +
                'M' + rs + ',' + rs + 'H-' + rs + 'V-' + rs + 'H' + rs + 'Z';
        },
        needLine: true,
        noDot: true
    },
    'diamond-cross': {
        n: 31,
        f: r => {
            var rd = d3round(r * 1.3, 2);
            return 'M' + rd + ',0L0,' + rd + 'L-' + rd + ',0L0,-' + rd + 'Z' +
                'M0,-' + rd + 'V' + rd + 'M-' + rd + ',0H' + rd;
        },
        needLine: true,
        noDot: true
    },
    'diamond-x': {
        n: 32,
        f: r => {
            var rd = d3round(r * 1.3, 2);
            var r2 = d3round(r * 0.65, 2);
            return 'M' + rd + ',0L0,' + rd + 'L-' + rd + ',0L0,-' + rd + 'Z' +
                'M-' + r2 + ',-' + r2 + 'L' + r2 + ',' + r2 +
                'M-' + r2 + ',' + r2 + 'L' + r2 + ',-' + r2;
        },
        needLine: true,
        noDot: true
    },
    'cross-thin': {
        n: 33,
        f: r => {
            var rc = d3round(r * 1.4, 2);
            return 'M0,' + rc + 'V-' + rc + 'M' + rc + ',0H-' + rc;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'x-thin': {
        n: 34,
        f: r => {
            var rx = d3round(r, 2);
            return 'M' + rx + ',' + rx + 'L-' + rx + ',-' + rx +
                'M' + rx + ',-' + rx + 'L-' + rx + ',' + rx;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    asterisk: {
        n: 35,
        f: r => {
            var rc = d3round(r * 1.2, 2);
            var rs = d3round(r * 0.85, 2);
            return 'M0,' + rc + 'V-' + rc + 'M' + rc + ',0H-' + rc +
                'M' + rs + ',' + rs + 'L-' + rs + ',-' + rs +
                'M' + rs + ',-' + rs + 'L-' + rs + ',' + rs;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    hash: {
        n: 36,
        f: r => {
            var r1 = d3round(r / 2, 2);
            var r2 = d3round(r, 2);
            return 'M' + r1 + ',' + r2 + 'V-' + r2 +
                'm-' + r2 + ',0V' + r2 +
                'M' + r2 + ',' + r1 + 'H-' + r2 +
                'm0,-' + r2 + 'H' + r2;
        },
        needLine: true,
        noFill: true
    },
    'y-up': {
        n: 37,
        f: r => {
            var x = d3round(r * 1.2, 2);
            var y0 = d3round(r * 1.6, 2);
            var y1 = d3round(r * 0.8, 2);
            return 'M-' + x + ',' + y1 + 'L0,0M' + x + ',' + y1 + 'L0,0M0,-' + y0 + 'L0,0';
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'y-down': {
        n: 38,
        f: r => {
            var x = d3round(r * 1.2, 2);
            var y0 = d3round(r * 1.6, 2);
            var y1 = d3round(r * 0.8, 2);
            return 'M-' + x + ',-' + y1 + 'L0,0M' + x + ',-' + y1 + 'L0,0M0,' + y0 + 'L0,0';
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'y-left': {
        n: 39,
        f: r => {
            var y = d3round(r * 1.2, 2);
            var x0 = d3round(r * 1.6, 2);
            var x1 = d3round(r * 0.8, 2);
            return 'M' + x1 + ',' + y + 'L0,0M' + x1 + ',-' + y + 'L0,0M-' + x0 + ',0L0,0';
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'y-right': {
        n: 40,
        f: r => {
            var y = d3round(r * 1.2, 2);
            var x0 = d3round(r * 1.6, 2);
            var x1 = d3round(r * 0.8, 2);
            return 'M-' + x1 + ',' + y + 'L0,0M-' + x1 + ',-' + y + 'L0,0M' + x0 + ',0L0,0';
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'line-ew': {
        n: 41,
        f: r => {
            var rc = d3round(r * 1.4, 2);
            return 'M' + rc + ',0H-' + rc;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'line-ns': {
        n: 42,
        f: r => {
            var rc = d3round(r * 1.4, 2);
            return 'M0,' + rc + 'V-' + rc;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'line-ne': {
        n: 43,
        f: r => {
            var rx = d3round(r, 2);
            return 'M' + rx + ',-' + rx + 'L-' + rx + ',' + rx;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'line-nw': {
        n: 44,
        f: r => {
            var rx = d3round(r, 2);
            return 'M' + rx + ',' + rx + 'L-' + rx + ',-' + rx;
        },
        needLine: true,
        noDot: true,
        noFill: true
    },
    'arrow-up': {
        n: 45,
        f: r => {
            var rx = d3round(r, 2);
            var ry = d3round(r * 2, 2);
            return 'M0,0L-' + rx + ',' + ry + 'H' + rx + 'Z';
        },
        noDot: true
    },
    'arrow-down': {
        n: 46,
        f: r => {
            var rx = d3round(r, 2);
            var ry = d3round(r * 2, 2);
            return 'M0,0L-' + rx + ',-' + ry + 'H' + rx + 'Z';
        },
        noDot: true
    },
    'arrow-left': {
        n: 47,
        f: r => {
            var rx = d3round(r * 2, 2);
            var ry = d3round(r, 2);
            return 'M0,0L' + rx + ',-' + ry + 'V' + ry + 'Z';
        },
        noDot: true
    },
    'arrow-right': {
        n: 48,
        f: r => {
            var rx = d3round(r * 2, 2);
            var ry = d3round(r, 2);
            return 'M0,0L-' + rx + ',-' + ry + 'V' + ry + 'Z';
        },
        noDot: true
    },
    'arrow-bar-up': {
        n: 49,
        f: r => {
            var rx = d3round(r, 2);
            var ry = d3round(r * 2, 2);
            return 'M-' + rx + ',0H' + rx + 'M0,0L-' + rx + ',' + ry + 'H' + rx + 'Z';
        },
        needLine: true,
        noDot: true
    },
    'arrow-bar-down': {
        n: 50,
        f: r => {
            var rx = d3round(r, 2);
            var ry = d3round(r * 2, 2);
            return 'M-' + rx + ',0H' + rx + 'M0,0L-' + rx + ',-' + ry + 'H' + rx + 'Z';
        },
        needLine: true,
        noDot: true
    },
    'arrow-bar-left': {
        n: 51,
        f: r => {
            var rx = d3round(r * 2, 2);
            var ry = d3round(r, 2);
            return 'M0,-' + ry + 'V' + ry + 'M0,0L' + rx + ',-' + ry + 'V' + ry + 'Z';
        },
        needLine: true,
        noDot: true
    },
    'arrow-bar-right': {
        n: 52,
        f: r => {
            var rx = d3round(r * 2, 2);
            var ry = d3round(r, 2);
            return 'M0,-' + ry + 'V' + ry + 'M0,0L-' + rx + ',-' + ry + 'V' + ry + 'Z';
        },
        needLine: true,
        noDot: true
    }
};

const DOTPATH = 'M0,0.5L0.5,0L0,-0.5L-0.5,0Z';

const drawing = {
    symbolFuncs: [],
};

/**
 * Create arrays of symbol functions.
 * https://plotly.com/javascript/reference/scatter/#scatter-marker-symbol
 */
Object.keys(SYMBOLDEFS).forEach(function(k) {
    var symDef = SYMBOLDEFS[k];
    var n = symDef.n;
    drawing.symbolFuncs[n] = symDef.f;
});

/**
 * Returns a <path></path> element that have to be placed in a <svg></svg> element.
 * 
 * @param {int} symbolNumber
 * @param {String} color
 * @return {Element}
 */
const createPathElement = (symbolNumber, color) => {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    // d is the shape of the symbol.
    path.setAttribute('d', createPathString(symbolNumber, 5));
    // Translation must be the half of the svg size to have the symbol centered.
    path.setAttribute('transform', 'translate(15, 15)');

    // If svg is type "open" or "open-dot" : https://plotly.com/javascript/reference/scatter/#scatter-marker-symbol
    if ((100 <= symbolNumber && symbolNumber < 200) || 300 <= symbolNumber) {
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', 0.5);
        path.setAttribute('stroke-opacity', 1);
        path.setAttribute('fill', 'white');
    }

    // If svg is type "normal" or "dot" : https://plotly.com/javascript/reference/scatter/#scatter-marker-symbol
    if (symbolNumber < 100 || (200 <= symbolNumber && symbolNumber < 300)) {
        path.setAttribute('fill-opacity', 1);
        path.setAttribute('fill', color);
    }

    // If svg is type "dot" : https://plotly.com/javascript/reference/scatter/#scatter-marker-symbol
    if (200 <= symbolNumber && symbolNumber < 300) {
        path.setAttribute('stroke', 'black');
        path.setAttribute('stroke-width', 0.5);
        path.setAttribute('stroke-opacity', 1);
    }
    
    return path;
}

/**
 * Returns the string corresponding of the symbol shape requested by symbolNumber.
 * 
 * @param {int} symbolNumber
 * @param {int} r size of the symbol (currently, we request a 5)
 * @returns {String} this string must be placed in the "d" attribute of <path></path> SVG element.
 */
function createPathString(symbolNumber, r) {
    var base = symbolNumber % 100;
    return drawing.symbolFuncs[base](r) + (symbolNumber >= 200 ? DOTPATH : '');
}
