import { X, Brain, Target, TrendingUp, TrendingDown, Award, Eye, BookText, Puzzle, MessageSquare, Zap, Clock, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { teacherAPI, analyticsAPI } from '@/lib/api';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';

const LEARNING_STYLE_ICONS = {
    'visual': Eye,
    'reading': BookText,
    'problem_solving': Puzzle,
    'explanation': MessageSquare
};

export default function StudentLearningDNAModal({ student, onClose }) {
    const [loading, setLoading] = useState(true);
    const [profileData, setProfileData] = useState(null);
    const [masteryData, setMasteryData] = useState(null);
    const [analyticsData, setAnalyticsData] = useState({
        dashboard: null,
        performance: null,
        weakTopics: [],
        chartData: []
    });
    const [activeTab, setActiveTab] = useState('overview'); // 'overview' or 'analytics'

    useEffect(() => {
        if (student?.id) {
            fetchStudentData();
        }
    }, [student]);

    const fetchStudentData = async () => {
        setLoading(true);
        try {
            // Fetch all data in parallel
            const [profile, mastery, dashboard, performanceTrend, performancePred, weakTopics] = await Promise.allSettled([
                teacherAPI.getStudentLearningProfile(student.id),
                teacherAPI.getStudentMastery(student.id),
                analyticsAPI.getDashboard(student.id),
                analyticsAPI.getPerformanceTrend(student.id),
                analyticsAPI.getPredictPerformance(student.id),
                analyticsAPI.getWeakTopics(student.id)
            ]);

            // Handle Profile
            if (profile.status === 'fulfilled') setProfileData(profile.value);
            else console.warn("Could not fetch learning profile", profile.reason);

            // Handle Mastery
            if (mastery.status === 'fulfilled') setMasteryData(mastery.value);
            else console.warn("Could not fetch mastery data", mastery.reason);

            // Handle Analytics
            setAnalyticsData({
                dashboard: dashboard.status === 'fulfilled' ? dashboard.value : null,
                performance: performancePred.status === 'fulfilled' ? performancePred.value : null,
                weakTopics: weakTopics.status === 'fulfilled' ? weakTopics.value?.weak_topics || [] : [],
                chartData: performanceTrend.status === 'fulfilled' ? performanceTrend.value?.trends || [] : []
            });

        } catch (error) {
            console.error('Error fetching student data:', error);
        } finally {
            setLoading(false);
        }
    };

    const getMasteryColor = (score) => {
        if (score >= 0.8) return 'text-green-500';
        if (score >= 0.6) return 'text-primary';
        if (score >= 0.4) return 'text-yellow-500';
        return 'text-red-500';
    };

    const getMasteryBg = (score) => {
        if (score >= 0.8) return 'bg-green-500/10 border-green-500/20';
        if (score >= 0.6) return 'bg-primary/10 border-primary/20';
        if (score >= 0.4) return 'bg-yellow-500/10 border-yellow-500/20';
        return 'bg-red-500/10 border-red-500/20';
    };

    const LearningStyleIcon = profileData?.profile?.learning_style ?
        LEARNING_STYLE_ICONS[profileData.profile.learning_style] : Brain;

    // Analytics Processed Data
    const avgResponseTime = analyticsData.dashboard?.time_spent_minutes && analyticsData.dashboard?.total_questions_answered
        ? Math.round((analyticsData.dashboard.time_spent_minutes * 60) / analyticsData.dashboard.total_questions_answered) + 's'
        : 'N/A';

    const radarData = analyticsData.weakTopics.slice(0, 5).map(topic => ({
        subject: topic.topic_name.substring(0, 10),
        A: topic.accuracy,
        fullSubject: topic.topic_name
    }));

    const finalRadarData = radarData.length > 0 ? radarData : [
        { subject: 'Focus', A: 80 },
        { subject: 'Speed', A: 65 },
        { subject: 'Accuracy', A: 90 },
        { subject: 'Consistency', A: 70 },
        { subject: 'Resilience', A: 85 },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300" onClick={onClose} />
            <div className="relative bg-[#0f111a] border border-white/10 rounded-[2rem] w-full max-w-5xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col ring-1 ring-white/10 animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-primary/10 to-transparent shrink-0">
                    <div>
                        <h2 className="text-2xl font-bold text-white tracking-tight">{student.name}</h2>
                        <p className="text-sm text-slate-400 font-medium">{student.email}</p>
                    </div>
                    <div className="flex items-center gap-4">
                        {/* Tabs */}
                        <div className="flex bg-black/40 p-1.5 rounded-xl border border-white/5">
                            <button
                                onClick={() => setActiveTab('overview')}
                                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'overview'
                                    ? 'bg-primary text-white shadow-md shadow-primary/20'
                                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                DNA & Mastery
                            </button>
                            <button
                                onClick={() => setActiveTab('analytics')}
                                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'analytics'
                                    ? 'bg-primary text-white shadow-md shadow-primary/20'
                                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                Deep Analytics
                            </button>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-3 hover:bg-white/10 rounded-xl transition-colors text-slate-400 hover:text-white"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                        </div>
                    ) : (
                        <>
                            {activeTab === 'overview' && (
                                <div className="space-y-6 animate-in fade-in slide-in-from-left-4 duration-300">
                                    {!profileData ? (
                                        <div className="text-center py-12">
                                            <Brain className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                                            <p className="text-muted-foreground">Student has not completed onboarding yet</p>
                                        </div>
                                    ) : (
                                        <>
                                            {/* DNA Profile Section */}
                                            <div className="bg-primary/5 border border-primary/10 rounded-xl p-6">
                                                <div className="flex items-center gap-3 mb-4">
                                                    <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                                                        <LearningStyleIcon className="w-5 h-5 text-primary" />
                                                    </div>
                                                    <h3 className="text-lg font-bold text-foreground">Learning DNA Profile</h3>
                                                </div>

                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                    <div>
                                                        <p className="text-xs text-muted-foreground mb-1 font-medium">Learning Style</p>
                                                        <p className="font-bold text-foreground capitalize">{profileData.profile.learning_style_display}</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-xs text-muted-foreground mb-1 font-medium">Current Ability</p>
                                                        <p className="font-bold text-primary">{profileData.profile.current_ability?.toFixed(2) || 'N/A'}</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-xs text-muted-foreground mb-1 font-medium">Learning Speed</p>
                                                        <p className="font-bold text-foreground">{profileData.profile.learning_speed?.toFixed(2)}x</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-xs text-muted-foreground mb-1 font-medium">Consistency</p>
                                                        <p className="font-bold text-foreground">{(profileData.profile.consistency_score * 100)?.toFixed(0)}%</p>
                                                    </div>
                                                </div>

                                                {/* Subject Confidences */}
                                                {profileData.profile.subject_confidences && profileData.profile.subject_confidences.length > 0 && (
                                                    <div className="mt-4 pt-4 border-t border-primary/10">
                                                        <p className="text-sm font-semibold text-foreground mb-3">Subject Confidence Levels</p>
                                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                                            {profileData.profile.subject_confidences.map((conf) => (
                                                                <div key={conf.id} className="bg-background/80 rounded-md p-3 border border-border">
                                                                    <p className="text-xs text-muted-foreground capitalize font-medium">{conf.subject_display}</p>
                                                                    <div className="flex items-center gap-2 mt-1">
                                                                        <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                                                                            <div
                                                                                className="h-full bg-primary rounded-full"
                                                                                style={{ width: `${(conf.confidence_level / 5) * 100}%` }}
                                                                            />
                                                                        </div>
                                                                        <span className="text-xs font-bold text-foreground">{conf.confidence_level}/5</span>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Mastery Overview Section */}
                                            {masteryData && masteryData.total_concepts > 0 && (
                                                <>
                                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                        <div className="bg-primary/5 border border-primary/20 rounded-xl p-5">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <Target className="w-4 h-4 text-primary" />
                                                                <span className="text-xs font-bold text-primary uppercase tracking-wider">Overall Mastery</span>
                                                            </div>
                                                            <div className="text-3xl font-bold text-foreground">{(masteryData.overall_mastery * 100).toFixed(0)}%</div>
                                                        </div>

                                                        <div className="bg-green-50/50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30 rounded-xl p-5">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <Award className="w-4 h-4 text-green-600 dark:text-green-400" />
                                                                <span className="text-xs font-bold text-green-700 dark:text-green-400 uppercase tracking-wider">Mastered</span>
                                                            </div>
                                                            <div className="text-3xl font-bold text-foreground">{masteryData.mastered_concepts}</div>
                                                            <p className="text-xs text-muted-foreground mt-1">of {masteryData.total_concepts} concepts</p>
                                                        </div>

                                                        <div className="bg-yellow-50/50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-900/30 rounded-xl p-5">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <TrendingDown className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                                                                <span className="text-xs font-bold text-yellow-700 dark:text-yellow-400 uppercase tracking-wider">Needs Practice</span>
                                                            </div>
                                                            <div className="text-3xl font-bold text-foreground">{masteryData.weak_concepts?.length || 0}</div>
                                                        </div>
                                                    </div>

                                                    {/* Subject Breakdown */}
                                                    {masteryData.mastery_by_subject && Object.keys(masteryData.mastery_by_subject).length > 0 && (
                                                        <div className="card-enterprise p-6">
                                                            <h3 className="text-lg font-bold text-foreground mb-4">Mastery by Subject</h3>
                                                            <div className="space-y-4">
                                                                {Object.entries(masteryData.mastery_by_subject).map(([subject, score]) => (
                                                                    <div key={subject}>
                                                                        <div className="flex items-center justify-between mb-1.5">
                                                                            <span className="font-semibold text-foreground capitalize text-sm">{subject.replace('_', ' ')}</span>
                                                                            <span className={`font-bold text-sm ${getMasteryColor(score)}`}>{(score * 100).toFixed(0)}%</span>
                                                                        </div>
                                                                        <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
                                                                            <div
                                                                                className={`absolute inset-y-0 left-0 rounded-full transition-all ${score >= 0.8 ? 'bg-green-500' :
                                                                                    score >= 0.6 ? 'bg-primary' :
                                                                                        score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                                                                    }`}
                                                                                style={{ width: `${score * 100}%` }}
                                                                            />
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Weak Concepts */}
                                                    {masteryData.weak_concepts && masteryData.weak_concepts.length > 0 && (
                                                        <div className="card-enterprise p-6">
                                                            <div className="flex items-center gap-2 mb-4">
                                                                <TrendingDown className="w-5 h-5 text-red-500" />
                                                                <h3 className="text-lg font-bold text-foreground">Concepts Needing Attention</h3>
                                                            </div>
                                                            <div className="space-y-2">
                                                                {masteryData.weak_concepts.map((concept, index) => (
                                                                    <div key={index} className={`p-3 rounded-lg border ${getMasteryBg(concept.mastery_score)}`}>
                                                                        <div className="flex items-center justify-between">
                                                                            <span className="font-semibold text-foreground text-sm">{concept.concept_id.replace(/_/g, ' ')}</span>
                                                                            <span className={`font-bold text-sm ${getMasteryColor(concept.mastery_score)}`}>
                                                                                {(concept.mastery_score * 100).toFixed(0)}%
                                                                            </span>
                                                                        </div>
                                                                        <p className="text-xs text-muted-foreground mt-1">
                                                                            {concept.attempts} attempts • {((concept.correct_count / concept.attempts) * 100).toFixed(0)}% accuracy
                                                                        </p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}

                            {activeTab === 'analytics' && (
                                <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300 pb-4">
                                    {/* Metrics Grid */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        <MetricCard
                                            title="Learning Rate"
                                            value={analyticsData.performance?.recent_trend === 'improving' ? 'High' : (analyticsData.performance?.recent_trend === 'declining' ? 'Low' : 'Stable')}
                                            subValue={analyticsData.performance?.recent_trend === 'improving' ? 'Improving trend' : 'Consistent pace'}
                                            icon={Zap}
                                            color="text-amber-600"
                                            bgColor="bg-amber-500/10"
                                        />
                                        <MetricCard
                                            title="Consistency"
                                            value={analyticsData.performance?.consistency === 'high' ? '90%' : (analyticsData.performance?.consistency === 'medium' ? '75%' : '50%')}
                                            subValue={analyticsData.performance?.consistency === 'high' ? 'Great streak!' : 'Keep practicing'}
                                            icon={Target}
                                            color="text-emerald-600"
                                            bgColor="bg-emerald-500/10"
                                        />
                                        <MetricCard
                                            title="Avg Response Time"
                                            value={avgResponseTime}
                                            subValue={analyticsData.dashboard?.total_questions_answered ? `${analyticsData.dashboard.total_questions_answered} questions` : 'No data'}
                                            icon={Clock}
                                            color="text-primary"
                                            bgColor="bg-primary/10"
                                        />
                                        <MetricCard
                                            title="Focus Score"
                                            value={analyticsData.performance?.predicted_score ? (analyticsData.performance.predicted_score / 10).toFixed(1) : 'N/A'}
                                            subValue={`Confidence: ${analyticsData.performance?.confidence || 'Low'}`}
                                            icon={Brain}
                                            color="text-purple-500"
                                            bgColor="bg-purple-500/10"
                                        />
                                    </div>

                                    {/* Charts Row */}
                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                        {/* Performance History */}
                                        <div className="card-enterprise p-6">
                                            <h3 className="text-lg font-bold mb-6 text-foreground">Performance History</h3>
                                            <div className="h-[250px]">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={analyticsData.chartData}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                                                        <XAxis
                                                            dataKey="date"
                                                            stroke="hsl(var(--muted-foreground))"
                                                            fontSize={12}
                                                            tickLine={false}
                                                            axisLine={false}
                                                            dy={10}
                                                            tickFormatter={(date) => {
                                                                if (!date) return '';
                                                                const d = new Date(date);
                                                                if (isNaN(d)) return date;
                                                                return d.toLocaleDateString('en-GB');
                                                            }}
                                                        />
                                                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} dx={-10} />
                                                        <Tooltip
                                                            contentStyle={{
                                                                backgroundColor: 'hsl(var(--card))',
                                                                borderColor: 'hsl(var(--border))',
                                                                color: 'hsl(var(--foreground))',
                                                                borderRadius: '12px',
                                                                border: '1px solid hsl(var(--border))',
                                                                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                                                            }}
                                                            itemStyle={{ color: 'hsl(var(--primary))' }}
                                                        />
                                                        <Line type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ fill: 'hsl(var(--primary))', r: 4 }} activeDot={{ r: 6 }} />
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>

                                        {/* Topic Accuracy Radar */}
                                        <div className="card-enterprise p-6">
                                            <h3 className="text-lg font-bold mb-6 text-foreground">Topic Accuracy Profile</h3>
                                            <div className="h-[250px]">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <RadarChart data={finalRadarData}>
                                                        <PolarGrid stroke="hsl(var(--border))" opacity={0.5} />
                                                        <PolarAngleAxis dataKey="subject" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12, fontWeight: 'bold' }} />
                                                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                                        <Radar name="Accuracy" dataKey="A" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.3} />
                                                        <Tooltip
                                                            contentStyle={{
                                                                backgroundColor: 'hsl(var(--card))',
                                                                borderColor: 'hsl(var(--border))',
                                                                color: 'hsl(var(--foreground))',
                                                                borderRadius: '12px',
                                                                border: '1px solid hsl(var(--border))'
                                                            }}
                                                        />
                                                    </RadarChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Recommended Learning Path */}
                                    <div className="card-enterprise p-6">
                                        <h3 className="text-lg font-bold mb-6 flex items-center gap-2 text-foreground">
                                            <TrendingUp className="w-5 h-5 text-primary" />
                                            Recommended Learning Focus
                                        </h3>
                                        <div className="relative pl-2">
                                            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border" />
                                            <div className="space-y-6 relative">
                                                {analyticsData.weakTopics.length > 0 ? (
                                                    analyticsData.weakTopics.slice(0, 3).map((topic, index) => (
                                                        <TimelineItem
                                                            key={index}
                                                            title={`Master ${topic.topic_name}`}
                                                            desc={topic.recommendation || `Focus on improving accuracy (currently ${topic.accuracy}%)`}
                                                            status={index === 0 ? 'current' : 'pending'}
                                                        />
                                                    ))
                                                ) : (
                                                    <>
                                                        <TimelineItem
                                                            title="Master Core Concepts"
                                                            desc="Great job! The student has no weak topics. Encourage practicing advanced core concepts."
                                                            status="current"
                                                        />
                                                        <TimelineItem
                                                            title="Advanced Applications"
                                                            desc="Explore new advanced topics to challenge the student."
                                                            status="pending"
                                                        />
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

function MetricCard({ title, value, subValue, icon: Icon, color, bgColor }) {
    return (
        <div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between h-full">
            <div className="flex justify-between items-start mb-2">
                <div>
                    <p className="text-muted-foreground text-xs font-bold uppercase tracking-wider">{title}</p>
                    <h3 className="text-xl font-black mt-1 text-foreground">{value}</h3>
                </div>
                <div className={`p-2.5 rounded-xl ${bgColor}`}>
                    <Icon className={`w-4 h-4 ${color}`} />
                </div>
            </div>
            <p className={`text-xs font-semibold ${color}`}>{subValue}</p>
        </div>
    );
}

function TimelineItem({ title, desc, status }) {
    const statusColors = {
        complete: 'bg-emerald-500 border-emerald-500',
        current: 'bg-primary border-primary shadow-[0_0_10px_rgba(59,130,246,0.3)]',
        pending: 'bg-slate-200 border-slate-300 dark:bg-slate-700 dark:border-slate-600',
        locked: 'bg-slate-100 border-slate-200'
    };

    return (
        <div className="flex gap-4 items-start">
            <div className={`
        w-4 h-4 rounded-full border-2 flex-shrink-0 z-10 mt-1.5 box-content
        ${statusColors[status]} bg-background
      `} />
            <div className={`
        p-4 rounded-xl flex-1 transition-all border
        ${status === 'current' ? 'border-primary/30 bg-primary/5' : 'border-border bg-card'}
      `}>
                <h4 className="font-bold flex items-center justify-between text-sm text-foreground">
                    {title}
                    {status === 'current' && <span className="text-[10px] uppercase font-black px-2 py-0.5 bg-primary/20 text-primary rounded-md">In Progress</span>}
                </h4>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{desc}</p>
            </div>
        </div>
    );
}
