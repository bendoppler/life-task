//
//  Item.swift
//  LifeTask
//
//  Created by Do Thai Bao on 21/3/26.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
