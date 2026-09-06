'use client';

import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar
} from 'recharts';
import {
    TrendingUp,
    Users,
    Clock,
    Brain,
    Target
} from 'lucide-react';

const mockData = [
    { name: 'Week 1', score: 65, participation: 80 },
    { name: 'Week 2', score: 72, participation: 85 },
    { name: 'Week 3', score: 68, participation: 75 },
    { name: 'Week 4', score: 78, participation: 90 },
    { name: 'Week 5', score: 82, participation: 88 },
    { name: 'Week 6', score: 85, participation: 92 },
];

export default function AnalyticsTab({ classroom }) {
    if (!classroom) return null;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                            <TrendingUp className="w-5 h-5" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Average Mastery</p>
                            <h4 className="text-2xl font-bold text-foreground">78%</h4>
                        </div>
                    </div>
                    <div className="w-full bg-muted/50 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-emerald-500 h-full rounded-full" style={{ width: '78%' }}></div>
                    </div>
                </div>

                <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
                            <Users className="w-5 h-5" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Active Students</p>
                            <h4 className="text-2xl font-bold text-foreground">{classroom.students?.length || 0}</h4>
                        </div>
                    </div>
                    <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                        <span className="text-emerald-500 font-bold">+12%</span> from last week
                    </p>
                </div>

                <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
                            <Brain className="w-5 h-5" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Learning Pace</p>
                            <h4 className="text-2xl font-bold text-foreground">Fast</h4>
                        </div>
                    </div>
                    <p className="text-xs text-muted-foreground font-medium">Class is ahead of schedule</p>
                </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card p-6 rounded-3xl border border-border shadow-sm">
                    <h3 className="text-lg font-bold text-foreground mb-6 flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-primary" />
                        Performance Trend
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={mockData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                <XAxis
                                    dataKey="name"
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => `${value}%`}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '12px', color: '#f8fafc' }}
                                    itemStyle={{ color: '#f8fafc' }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="score"
                                    stroke="#6366f1"
                                    strokeWidth={3}
                                    dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }}
                                    activeDot={{ r: 6 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="bg-card p-6 rounded-3xl border border-border shadow-sm">
                    <h3 className="text-lg font-bold text-foreground mb-6 flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-500" />
                        Participation Rate
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={mockData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                <XAxis
                                    dataKey="name"
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: '#ffffff05' }}
                                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '12px', color: '#f8fafc' }}
                                />
                                <Bar dataKey="participation" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
