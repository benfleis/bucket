// monkey patch emitter to do emitter.on(*, cb)
function tapEventEmitter(emitter, cb) {
    var emit = emitter.emit;
    emitter.emit = function() {
        cb.apply(emitter, arguments);
        emit.apply(emitter, arguments);
    }
}
