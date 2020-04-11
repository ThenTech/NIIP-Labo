var span = 250;
var prev = 0;
let input_text  = document.getElementById("text");
let input_bps   = document.getElementById("bps");
let transmitter = document.getElementById("transmit-box");

let start_symbol = "11110011";
let stop_symbol  = stringToBytes('\n')[0];

function transmit() {
    prev = 0
    const text = input_text.value;
    span = 1000 / +input_bps.value;
    console.log(span);

    const bytes = stringToBytes(text);
    console.log(`Send: ${start_symbol} + [${bytes}] + ${stop_symbol}, `
              + `taking ${((1 + bytes.length + 1) * 8 * span) / 1000} seconds.`);
    transmitBytes(bytes);
}

async function transmitBytes(bytes, str = "") {
    //Send start
    console.log("Send start");
    await sendByte(start_symbol);

    console.log("Send text")
    for (var i = 0; i < bytes.length; i++) {
        await sendByte(bytes[i]);
    }

    console.log("Send stop")
    await sendByte(stop_symbol);

    console.log("Reset background to white")
    await sendBit(1);
}

function stringToBytes(str) {
    return toUTF8Array(str).map(item => toBinary(item))
}

function sendByte(byteStr) {
    return recursiveTransmit(byteStr)
}

function recursiveTransmit(chars, i = 0) {
    if (i < chars.length) {
        return sendBit(chars[i]).then(_ => recursiveTransmit(chars, i + 1));
    } else {
        return Promise.resolve();
    }
}

function toBinary(val, pad_length=8) {
    return (val).toString(2).padStart(pad_length, '0');
}

function sendBit(bit) {
    // Recalc delay to keep in sync
    var diff = (prev == 0 ? span : Date.now() - prev);
    prev = Date.now()
    delay = span + (span - diff)

    return new Promise(resolve => setTimeout(function () {
        var vis = (bit == '1' ? "white" : "black");
        transmitter.style.background = vis;

        console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        resolve();
    }, delay));
}

function toUTF8Array(str) {
    let utf8 = [];

    for (let i = 0; i < str.length; i++) {
        let charcode = str.charCodeAt(i);

        if (charcode < 0x80) {
            utf8.push(charcode);
        } else if (charcode < 0x800) {
            utf8.push(0xc0 | (charcode >> 6),
                      0x80 | (charcode & 0x3f));
        } else if (charcode < 0xd800 || charcode >= 0xe000) {
            utf8.push(0xe0 | (charcode >> 12),
                      0x80 | ((charcode >> 6) & 0x3f),
                      0x80 | (charcode & 0x3f));
        } else {
            // surrogate pair
            i++;
            // UTF-16 encodes 0x10000-0x10FFFF by
            // subtracting 0x10000 and splitting the
            // 20 bits of 0x0-0xFFFFF into two halves
            charcode = 0x10000 + (((charcode & 0x3ff) << 10) |
                                    (str.charCodeAt(i) & 0x3ff));
            utf8.push(0xf0 | (charcode >> 18),
                      0x80 | ((charcode >> 12) & 0x3f),
                      0x80 | ((charcode >> 6) & 0x3f),
                      0x80 | (charcode & 0x3f));
        }
    }

    return utf8;
}
