var span = 250;

function transmit() {
    var text = document.getElementById("text").value;
    start();
}
async function start() {
    await sendBit(0);
    await sendBit(0);
    await sendBit(1);
    await sendBit(1);

}
function sendBit(bit) {
    return new Promise(resolve => setTimeout(function() {
        var vis = "black";
        if(bit) {
            vis = "white";
        }
        document.getElementById("transmit-box").style.background = vis;
        console.log("Color set to " + vis)
        resolve();
    }, span));
}